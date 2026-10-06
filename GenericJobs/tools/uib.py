"""Reader (and, for the edits the mod needs, writer) for IC's UI layout files (.uib), after AlexCup and Nenkai's 010
Editor template for Final Fantasy XVI's (Nenkai/010GameTemplates, Square Enix/Final Fantasy 16/FF16_uib_UIBinary.bt;
IC's files are the same format, version 10).

  python tools/uib.py <file.uib> [component]      prints the components, or one component's nodes and timelines

Format essentials (every offset is relative to the start of the structure that holds it):
  header: 'UIB\\0', u32 version (10), 16 bytes, u32 TOC offset (0x2C)
  TOC (0x2C): asset list offset, component table offset, component count
  component (GroupEntry, 0x40 bytes): name, size (w, h), properties, nodes (offset, count), timelines (offset, count)
  node list: u32 offsets (relative to the list) to nodes; node: +0 type (1 layer, 2 image, 3 text, 4 ninegrid,
    6 rect, 7 ellipse, 8 bezier, 10 reference = an instance of another component, 11 effect, 13 mask), +4 name,
    +8 origin (x, y), +0x10 rotation, +0x14 scale, +0x1C anchor, +0x44 size, +0x4C data offset; layers: children at
    +0x90 (offset) / +0x94 (count); references: the component's name at +0x70
  timeline (UIComponentTimeline, 0x60 bytes): name, flags, info at +8 {type, elements (offset, count), asset groups,
    targets (offset, count), frame count}; element (0x20 bytes): index, name, type, frame start, frame count, target
    index, 2 bools, data offset (the keyframe data: type, 0x2C bytes, value(s) at +0x30.. / +0x74)
"""
import struct, sys

class Uib:
    def __init__(self, path_or_bytes):
        self.d = bytearray(open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes)
        d = self.d
        assert d[:4] == b'UIB\0', 'not a UIB file'
        self.version = self.u32(4)
        self.toc = self.u32(0x18)
        self.comp_table = self.toc + self.i32(self.toc + 4)
        self.comp_count = self.i32(self.toc + 8)

    # --- primitives ---
    def u32(self, o): return struct.unpack_from('<I', self.d, o)[0]
    def i32(self, o): return struct.unpack_from('<i', self.d, o)[0]
    def f32(self, o): return struct.unpack_from('<f', self.d, o)[0]
    def cstr(self, o):
        e = self.d.index(b'\0', o); return self.d[o:e].decode('utf-8', 'replace')
    def rel_str(self, base, field):
        off = self.i32(field)
        return self.cstr(base + off) if off else None

    # --- components ---
    def component(self, k):
        b = self.comp_table + 0x40 * k
        return dict(index=k, base=b, name=self.rel_str(b, b), w=self.i32(b + 4), h=self.i32(b + 8),
                    props=b + self.i32(b + 0xC), nodes=b + self.i32(b + 0x10), node_count=self.i32(b + 0x14),
                    timelines=b + self.i32(b + 0x18), timeline_count=self.i32(b + 0x1C))

    def components(self):
        return [self.component(k) for k in range(self.comp_count)]

    def find(self, name):
        return next(c for c in self.components() if c['name'] == name)

    # --- nodes ---
    def node_list(self, at, count):
        return [self.node(at + self.i32(at + 4 * i)) for i in range(count)]

    def node(self, b):
        t = self.i32(b)
        n = dict(base=b, type=t, name=self.rel_str(b, b + 4), x=self.i32(b + 8), y=self.i32(b + 0xC),
                 rot=self.f32(b + 0x10), sx=self.f32(b + 0x14), sy=self.f32(b + 0x18),
                 ax=self.i32(b + 0x1C), ay=self.i32(b + 0x20), w=self.i32(b + 0x44), h=self.i32(b + 0x48),
                 data=b + self.i32(b + 0x4C))
        if t == 1:                                   # layer: children (offset, count at +0x90 / +0x94)
            n['children'] = self.node_list(b + self.i32(b + 0x90), self.u32(b + 0x94))
        elif t == 10:                                # reference: an instance of another component (name at +0x70)
            n['ref'] = self.rel_str(b, b + 0x70)
        return n

    # --- timelines ---
    def timelines(self, comp):
        return [self.timeline(comp['timelines'] + 0x60 * i) for i in range(comp['timeline_count'])]

    def timeline(self, b):
        info = b + 8
        el_at, el_n = info + self.i32(info + 4), self.i32(info + 8)
        tg_at, tg_n = info + self.i32(info + 0x14), self.i32(info + 0x18)
        return dict(base=b, name=self.rel_str(b, b), flags=self.u32(b + 4), type=self.i32(info),
                    frames=self.i32(info + 0x1C), elements=[self.element(el_at + 0x20 * i) for i in range(el_n)],
                    targets=[self.target(tg_at, i) for i in range(tg_n)])

    def target(self, list_at, i):
        b = list_at + self.i32(list_at + 4 * i)
        t = self.i32(b)
        return dict(base=b, type=t, name=self.rel_str(b, b + 0x28) if t == 4001 else None)

    def element(self, b):
        data = b + self.i32(b + 0x1C)
        e = dict(base=b, index=self.i32(b), name=self.rel_str(b, b + 4), type=self.i32(b + 8),
                 start=self.i32(b + 0xC), count=self.i32(b + 0x10), target=self.i32(b + 0x14),
                 data=data, dtype=self.i32(data))
        e['values'] = [self.f32(data + 0x74), self.f32(data + 0x78)] if e['dtype'] in (5004,) else \
                      [self.f32(data + 0x74)] if e['dtype'] in (5005, 5009) else \
                      [self.i32(data + 0x74), self.i32(data + 0x78)] if e['dtype'] in (5002, 5003) else []
        return e

    # --- every offset field of a component (for copying structures elsewhere in the file) ---
    def offset_fields(self, comp=None, node_at=None):
        """[(field address, struct base)] for every non-zero offset reachable from the component's properties, nodes
        and timelines, per the template (a structure's offsets are relative to its own start). With `node_at`, only
        that node's (and its children's)."""
        out, seen = [], set()
        def field(base, at):
            if self.i32(at): out.append((at, base)); return base + self.i32(at)
            return None
        def asset_entry(a):
            if a is None or ('a', a) in seen: return
            seen.add(('a', a)); field(a, a + 4)
            n = field(a, a + 8)
            if n is not None: field(n, n + 4)
        def texture_asset(t):
            if t is None: return
            asset_entry(field(t, t))
        def texture_assets(at, count, size=0x2C):
            for i in range(count): texture_asset(at + size * i)
        def node(b):
            if ('n', b) in seen: return
            seen.add(('n', b)); t = self.i32(b)
            field(b, b + 4)
            data = field(b, b + 0x4C)
            if t == 1:
                lst = field(b, b + 0x90)
                if lst is not None: node_list(lst, self.u32(b + 0x94))
            elif t == 10:
                field(b, b + 0x70); asset_entry(field(b, b + 0x74))
            elif t == 11:
                asset_entry(field(b, b + 0x74))
            elif t == 13:
                asset_entry(field(b, b + 0x9C)); field(b, b + 0xA0)
            if data is None: return
            if t in (2, 13):
                at = field(data, data + 0x40)
                if at is not None: texture_assets(at, self.i32(data + 0x44))
            elif t == 3:
                field(data, data + 0x44)
            elif t == 4:
                at = field(data, data + 0x40)
                if at is not None: texture_asset(at)
            elif t == 5:
                at = field(data, data + 0x40)
                if at is not None: texture_asset(at)
                field(data, data + 0x68); field(data, data + 0x6C)
            elif t == 7:
                at = field(data, data + 0x50)
                if at is not None: texture_asset(at)
            elif t == 8:
                field(data, data + 0x80)
        def node_list(at, count):
            for i in range(count):
                n = field(at, at + 4 * i)
                if n is not None: node(n)
        def timeline(m):
            field(m, m)
            info = m + 8
            el = field(info, info + 4)
            for i in range(self.i32(info + 8) if el is not None else 0):
                e = el + 0x20 * i
                field(e, e + 4)
                x = field(e, e + 0x1C)
                if x is not None and self.i32(x) == 5028: field(x, x + 0x30)
            ag = field(info, info + 0xC)
            for i in range(self.i32(info + 0x10) if ag is not None else 0):
                g = ag + 0xC * i
                lst = field(g, g + 4)
                for j in range(self.i32(g + 8) if lst is not None else 0):
                    asset_entry(field(lst, lst + 4 * j))
            tg = field(info, info + 0x14)
            for i in range(self.i32(info + 0x18) if tg is not None else 0):
                t = field(tg, tg + 4 * i)
                if t is not None and self.i32(t) == 4001: field(t, t + 0x28)
            field(m, m + 0x30); asset_entry(field(m, m + 0x34)); field(m, m + 0x3C)
        if node_at is not None:
            node(node_at)
            return out
        p = comp['props']
        names = field(p, p + 4)
        for i in range(self.i32(p + 8) if names is not None else 0): field(names, names + 4 * i)
        asset_entry(field(p, p + 0x98))
        if self.i32(p + 0xAC) > 0: texture_asset(field(p, p + 0xA8))
        if comp['node_count']: node_list(comp['nodes'], comp['node_count'])
        for i in range(comp['timeline_count']): timeline(comp['timelines'] + 0x60 * i)
        return out

    def extent(self, comp):
        """The byte range [lo, hi) the component's own structures occupy (targets in the shared string pool and
        asset data excluded), and its offset fields."""
        fields = self.offset_fields(comp)
        starts = [comp['props'], comp['nodes'], comp['timelines']] + [a for a, b in fields]
        return min(starts), fields

    def copy_component(self, source, target):
        """Makes component `target` a copy of component `source`: `source`'s structures are copied to the end of the
        file (every offset leaving the copied block re-aimed) and `target`'s record points at the copy. Returns the
        copy's delta (new address - old address) so its values can be edited."""
        src, dst = self.find(source), self.find(target)
        fields = self.offset_fields(src)
        lo = min([src['props'], src['nodes'], src['timelines']] + [a for a, b in fields] + [b for a, b in fields])
        nxt = sorted(c['props'] for c in self.components() if c['props'] > lo)
        hi = nxt[0] if nxt else len(self.d)
        pad = (-len(self.d)) % 16
        new_lo = len(self.d) + pad
        delta = new_lo - lo
        block = bytearray(self.d[lo:hi])
        for at, base in fields:
            if not lo <= at < hi: continue               # a field outside the block (none expected)
            target_addr = base + self.i32(at)
            if lo <= target_addr < hi: continue           # inside the block: moves with it
            struct.pack_into('<i', block, at - lo, target_addr - (base + delta))
        self.d += b'\0' * pad + block
        b = dst['base']
        for off, addr in ((0xC, src['props']), (0x10, src['nodes']), (0x18, src['timelines'])):
            struct.pack_into('<i', self.d, b + off, addr + delta - b)
        struct.pack_into('<i', self.d, b + 0x14, src['node_count'])
        struct.pack_into('<i', self.d, b + 0x1C, src['timeline_count'])
        return delta, lo, hi

    def add_string(self, s):
        """Appends a NUL-terminated string to the end of the file and returns its address."""
        at = len(self.d)
        self.d += s.encode() + b'\0'
        return at

    def set_layer_children(self, layer, nodes):
        """Points `layer` at a new child list (at the end of the file) holding `nodes`, in order."""
        self.d += b'\0' * ((-len(self.d)) % 16)
        lst = len(self.d)
        for c in nodes:
            self.d += struct.pack('<i', c['base'] - lst)        # child offsets are relative to the list
        b = layer['base']
        struct.pack_into('<i', self.d, b + 0x90, lst - b)
        struct.pack_into('<I', self.d, b + 0x94, len(nodes))
        layer['children'] = [self.node(c['base']) for c in nodes]

    def remove_children(self, layer, names):
        names = set(names)
        found = {c['name'] for c in layer['children']} & names
        assert found == names, names - found
        self.set_layer_children(layer, [c for c in layer['children'] if c['name'] not in names])

    def move_node(self, node, x, y):
        struct.pack_into('<2i', self.d, node['base'] + 8, x, y)

    def resize_node(self, node_base, w, h):
        """Size, and the pivot at its centre (as every node here has it)."""
        struct.pack_into('<2i', self.d, node_base + 0x44, w, h)
        struct.pack_into('<2i', self.d, node_base + 0x1C, w // 2, h // 2)

    def copy_node(self, source_base, layer, name, x, y, w=None, h=None, sx=None, sy=None):
        """Adds a copy of the node at `source_base` (from any layer or component) to `layer` as `name` at (x, y),
        optionally resized and scaled (-1 mirrors). The copied block runs from the node to just past its last offset
        field (its data and asset entries follow it); offsets leaving the block are re-aimed."""
        fields = self.offset_fields(node_at=source_base)
        lo, hi = source_base, max(at for at, _ in fields) + 4
        self.d += b'\0' * ((-len(self.d)) % 16)
        new_lo = len(self.d)
        block = bytearray(self.d[lo:hi])
        for at, base in fields:
            target_addr = base + self.i32(at)
            if lo <= target_addr < hi: continue
            struct.pack_into('<i', block, at - lo, target_addr - (base + new_lo - lo))
        self.d += block
        self.move_node(dict(base=new_lo), x, y)
        if w is not None: self.resize_node(new_lo, w, h)
        if sx is not None: struct.pack_into('<f', self.d, new_lo + 0x14, sx)
        if sy is not None: struct.pack_into('<f', self.d, new_lo + 0x18, sy)
        name_at = self.add_string(name)
        struct.pack_into('<i', self.d, new_lo + 4, name_at - new_lo)
        self.set_layer_children(layer, layer['children'] + [dict(base=new_lo)])
        return new_lo

    def add_timeline_targets(self, comp, timeline, names):
        """Appends node-name targets (type 4001 entries, 0x2C bytes, name offset at +0x28) to a component's timeline,
        in a new target list at the end of the file (existing indices are kept)."""
        t = next(t for t in self.timelines(comp) if t['name'] == timeline)
        info = t['base'] + 8
        old_at, n = info + self.i32(info + 0x14), self.i32(info + 0x18)
        template = next(x['base'] for x in t['targets'] if x['type'] == 4001)
        new_targets = []
        for name in names:
            self.d += b'\0' * ((-len(self.d)) % 4)
            b = len(self.d)
            self.d += self.d[template:template + 0x2C]
            name_at = self.add_string(name)
            struct.pack_into('<i', self.d, b + 0x28, name_at - b)
            new_targets.append(b)
        self.d += b'\0' * ((-len(self.d)) % 16)
        lst = len(self.d)
        for i in range(n):
            self.d += struct.pack('<i', old_at + self.i32(old_at + 4 * i) - lst)
        for b in new_targets:
            self.d += struct.pack('<i', b - lst)
        struct.pack_into('<i', self.d, info + 0x14, lst - info)
        struct.pack_into('<i', self.d, info + 0x18, n + len(names))

    # --- new components ---
    COMPONENT_OFFSETS = (0x0, 0xC, 0x10, 0x18, 0x24)     # record fields holding offsets (relative to the record)

    def grow_components(self, extra):
        """Moves the component table to the end of the file with room for `extra` more records (the TOC holds its
        offset and count; a record's offsets are relative to the record, so they're re-aimed). Returns the index of
        the first free record."""
        self.d += b'\0' * ((-len(self.d)) % 16)
        new = len(self.d)
        self.d += b'\0' * (0x40 * (self.comp_count + extra))
        for k in range(self.comp_count):
            old = self.comp_table + 0x40 * k
            self.d[new + 0x40 * k:new + 0x40 * (k + 1)] = self.d[old:old + 0x40]
            for f in self.COMPONENT_OFFSETS:
                v = self.i32(old + f)
                if v: struct.pack_into('<i', self.d, new + 0x40 * k + f, old + v - (new + 0x40 * k))
        first = self.comp_count
        struct.pack_into('<i', self.d, self.toc + 4, new - self.toc)
        self.comp_table, self.comp_count = new, self.comp_count + extra
        struct.pack_into('<i', self.d, self.toc + 8, self.comp_count)
        self._free_component = first
        return first

    def clone_node(self, source_base):
        """A copy of a node block (see copy_node) at the end of the file, in no layer; returns its address."""
        fields = self.offset_fields(node_at=source_base)
        lo, hi = source_base, max(at for at, _ in fields) + 4
        self.d += b'\0' * ((-len(self.d)) % 16)
        new_lo = len(self.d)
        block = bytearray(self.d[lo:hi])
        for at, base in fields:
            target_addr = base + self.i32(at)
            if lo <= target_addr < hi: continue
            struct.pack_into('<i', block, at - lo, target_addr - (base + new_lo - lo))
        self.d += block
        return new_lo

    def add_component(self, name, like, w, h, children):
        """Fills the next free component record (see grow_components) as `name`, w x h: a copy of component `like`'s
        root layer holding `children` (node addresses), sharing `like`'s properties and timelines (which target the
        root layer by name, so the children take its state colours)."""
        k = self._free_component
        assert k < self.comp_count, 'no free component record'
        self._free_component += 1
        src = self.find(like)
        root = self.clone_node(self.node_list(src['nodes'], src['node_count'])[0]['base'])
        struct.pack_into('<2i', self.d, root + 8, 0, 0)
        self.resize_node(root, w, h)
        layer = self.node(root)
        layer['children'] = []
        self.set_layer_children(layer, [dict(base=c) for c in children])
        self.d += b'\0' * ((-len(self.d)) % 16)
        lst = len(self.d)
        self.d += struct.pack('<i', root - lst)
        b, s = self.comp_table + 0x40 * k, src['base']
        self.d[b:b + 0x40] = self.d[s:s + 0x40]
        for f in self.COMPONENT_OFFSETS:
            v = self.i32(s + f)
            if v: struct.pack_into('<i', self.d, b + f, s + v - b)
        name_at = self.add_string(name)
        struct.pack_into('<i', self.d, b, name_at - b)
        struct.pack_into('<2i', self.d, b + 4, w, h)
        struct.pack_into('<i', self.d, b + 0x10, lst - b)
        struct.pack_into('<i', self.d, b + 0x14, 1)
        return k

    def image_piece(self, source_base, x, y, w, h, part=None, flip_x=False, flip_y=False):
        """A copy of image node `source_base` as a fixed piece: at (x, y), w x h, anchored top-left, optionally
        showing another texture part and flipped (image data +0x18 anchor flags L/T/R/B, +0x6C/+0x6D flips; the
        texture entry's part index at +8). Returns its address."""
        n = self.clone_node(source_base)
        struct.pack_into('<2i', self.d, n + 8, x, y)
        self.resize_node(n, w, h)
        data = n + self.i32(n + 0x4C)
        self.d[data + 0x18:data + 0x1C] = bytes([1, 1, 0, 0])
        self.d[data + 0x6C] = int(flip_x)
        self.d[data + 0x6D] = int(flip_y)
        if part is not None:
            tex = data + self.i32(data + 0x40)
            struct.pack_into('<i', self.d, tex + 8, part)
        return n

    def add_child(self, layer, source, name, x, y):
        """Adds a copy of node `source` (a child of `layer`, both node dicts) to `layer` as `name` at (x, y). The copy
        and a new child list (the old entries plus the copy) go at the end of the file; the copy's block runs from
        `source` to the next sibling (a node's data and asset entries sit right after it), and every offset leaving
        the block is re-aimed. Returns the copy's address."""
        kids = layer['children']
        i = next(k for k, c in enumerate(kids) if c['base'] == source['base'])
        lo = source['base']
        hi = kids[i + 1]['base'] if i + 1 < len(kids) else min(c['base'] for c in kids if c['base'] > lo)
        fields = self.offset_fields(node_at=lo)
        self.d += b'\0' * ((-len(self.d)) % 16)
        new_lo = len(self.d)
        block = bytearray(self.d[lo:hi])
        for at, base in fields:
            if not lo <= at < hi: continue
            target_addr = base + self.i32(at)
            if lo <= target_addr < hi: continue
            struct.pack_into('<i', block, at - lo, target_addr - (base + new_lo - lo))
        self.d += block
        struct.pack_into('<i', self.d, new_lo + 8, x)
        struct.pack_into('<i', self.d, new_lo + 0xC, y)
        name_at = self.add_string(name)
        struct.pack_into('<i', self.d, new_lo + 4, name_at - new_lo)
        self.d += b'\0' * ((-len(self.d)) % 16)
        lst = len(self.d)
        for c in kids + [dict(base=new_lo)]:
            self.d += struct.pack('<i', c['base'] - lst)        # child offsets are relative to the list
        b = layer['base']
        struct.pack_into('<i', self.d, b + 0x90, lst - b)
        struct.pack_into('<I', self.d, b + 0x94, len(kids) + 1)
        layer['children'] = kids + [self.node(new_lo)]
        return new_lo

    def save(self, path):
        open(path, 'wb').write(self.d)

def show_node(n, depth=0):
    extra = (' -> ' + n['ref']) if n.get('ref') else ''
    print('%s%s [%d] @(%d,%d) %dx%d%s' % ('  ' * depth, n['name'], n['type'], n['x'], n['y'], n['w'], n['h'], extra))
    for c in n.get('children', []): show_node(c, depth + 1)

if __name__ == '__main__':
    u = Uib(sys.argv[1])
    if len(sys.argv) < 3:
        for c in u.components():
            print('%2d %-20s %dx%d nodes %d timelines %d' % (c['index'], c['name'], c['w'], c['h'], c['node_count'], c['timeline_count']))
        sys.exit()
    c = u.find(sys.argv[2])
    print(c['name'], c['w'], c['h'])
    for n in u.node_list(c['nodes'], c['node_count']): show_node(n, 1)
    for t in u.timelines(c):
        print('timeline %s type %d frames %d targets %s' % (t['name'], t['type'], t['frames'], [x['name'] for x in t['targets']]))
        for e in t['elements']:
            print('    el %s type %d frames %d+%d target %d data %d %s' % (e['name'], e['type'], e['start'], e['count'], e['target'], e['dtype'], ['%.1f' % v if isinstance(v, float) else v for v in e['values']]))
