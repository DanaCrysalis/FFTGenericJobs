"""Job change screen layout (ui/ffto/unit/ffto_jobchange_ver03.uib): aligns the first and third rows of job slots with
the second, so all three rows use the same seven columns and the seventh spot of rows 1 and 3 is free.

  python tools/jobchange_layout.py <vanilla FFTIVC dir> <output FFTIVC dir>

Vanilla layout (UnitPosition component, LayerUnitPosition layer): Unit01..06 at y=12, Unit07..13 at y=214,
Unit14..19 at y=416, columns 270 apart. Row 2 starts at x=118; rows 1 and 3 start at x=254. Every x of a row 1/3
slot (node origin and timeline position keys) moves by -136, except ShowGuest's centred guest position. The
selection cursor's default spot (UnitSelect, SelectSpot) sits on slot 1 and moves with it.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uib import Uib

PATH = os.path.join('data', 'enhanced', 'ui', 'ffto', 'unit', 'ffto_jobchange_ver03.uib')

ROW2_X = 118
OLD_ROW13_X = 254
SHIFT = ROW2_X - OLD_ROW13_X
ROW13 = ['Unit%02d' % i for i in list(range(1, 7)) + list(range(14, 20))]
KEEP_TIMELINES = {'ShowGuest'}           # Unit01 is the lone guest/monster unit there, centred

def all_nodes(u, c):
    nodes = {}
    def walk(n):
        nodes[n['name']] = n
        for ch in n.get('children', []): walk(ch)
    for n in u.node_list(c['nodes'], c['node_count']): walk(n)
    return nodes

def move_node(u, node, dx):
    struct.pack_into('<i', u.d, node['base'] + 8, node['x'] + dx)

def move_keys(u, comp, names, dx, skip=()):
    moved = 0
    for t in u.timelines(comp):
        if t['name'] in skip: continue
        for e in t['elements']:
            if e['dtype'] != 5002: continue
            if t['targets'][e['target']]['name'] not in names: continue
            x, y = e['values']
            struct.pack_into('<2i', u.d, e['data'] + 0x74, x + dx, y)
            moved += 1
    return moved

def build(src_root, out_root):
    u = Uib(os.path.join(src_root, PATH))

    comp = u.find('UnitPosition')
    nodes = all_nodes(u, comp)
    for name in ROW13: move_node(u, nodes[name], SHIFT)
    assert nodes['UnitSelect']['x'] == OLD_ROW13_X
    move_node(u, nodes['UnitSelect'], SHIFT)
    moved = move_keys(u, comp, set(ROW13), SHIFT, KEEP_TIMELINES)

    spot = u.find('SelectSpot')
    layer = all_nodes(u, spot)['LayerPosition']
    assert layer['x'] == OLD_ROW13_X
    move_node(u, layer, SHIFT)
    moved += move_keys(u, spot, {'LayerPosition'}, SHIFT)

    out = os.path.join(out_root, PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    u.save(out)
    return out, moved

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out, moved = build(sys.argv[1], sys.argv[2])
    print('wrote %s (%d position keys moved)' % (out, moved))
