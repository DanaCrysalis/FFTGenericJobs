"""Job tree layout (ui/ffto/unit/ffto_job_tree.uib): Dark Knight and Onion Knight nodes, their requirement lines, and
the lines of Dragoon, which moves under Thief to make room for Dark Knight.

  python tools/jobtree_layout.py <vanilla FFTIVC dir> <output FFTIVC dir>

How the tree draws (JobTree component, LayerRoot):
- One UnitJob reference node per job, found by name (the game's slot -> name switch: Squire..Mime, and through the
  mod's hook DarkKnight / OnionKnight for slots 20 / 21).
- Requirement lines live in LayerBranches and are found by name: "Line<required><job>" (generaljob position types
  5/6 instead use a shared "Line<required>Lv<NN>" line). Each references one stretchable line component (LineBottom,
  LineRight, LineLeft, LineRightBottom, LineLeftBottom, LineBottomLeft, LineTopRight, LineBottomRightTop, ...); the
  node's box sets the stretch. Path conventions below (bar centrelines, arrow tips) were measured on vanilla lines.
- Level labels: position types 1-4 show the required job's own TextBoardJobLvL/R/B/T box (one per side); with the
  mod's hook, type 7 shows "LvLn<required><job>", a label node of its own added to UnitJob here and placed relative to
  the required job's node (UnitJob's LayerRoot sits at (0, 8)).
- Paths no component has (Knight / Geomancer / Black Mage -> Dark Knight) get a component of their own (PATHS): bar,
  rounded-corner and arrow images from the atlas at fixed places under a copy of LineRight's root layer, sharing
  LineRight's timelines, which colour that root layer (lock / unlock / cursor), so the whole path takes the state.
  The component table is moved to the end of the file to make room for them.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uib import Uib

PATH = os.path.join('data', 'enhanced', 'ui', 'ffto', 'unit', 'ffto_job_tree.uib')

DRAGOON = (200, 850)
NEW_NODES = [('DarkKnight', 404, 850), ('OnionKnight', 812, 280)]
REMOVED_LINES = ['LineThiefDragoon', 'LineDragoonSamurai', 'LineDragoonMime', 'LineDragoonDancer', 'LineKnightSamurai']

# --- line boxes from paths (points are bar centrelines, tips are arrow tips) ---
def bottom(x, y0, tip):                  # down
    return 'LineBottom', (x - 8, y0, 16, tip - 20 - y0)

def up(x, y0, tip):                      # up: LineBottom mirrored about its centre
    return 'LineBottom', (x - 8, tip + 20, 16, y0 - (tip + 20)), -1

def right(x0, y, tip):
    return 'LineRight', (x0, y - 5, tip - 20 - x0, 10)

def left(x0, y, tip):
    return 'LineLeft', (tip + 20, y - 5, x0 - (tip + 20), 10)

def right_bottom(x0, y0, xc, tip):
    return 'LineRightBottom', (x0, y0 - 8, xc + 8 - x0, tip - 20 - (y0 - 8))

def left_bottom(x0, y0, xc, tip):
    return 'LineLeftBottom', (xc - 8, y0 - 8, x0 - (xc - 8), tip - 20 - (y0 - 8))

def bottom_left(x0, y0, yc, tip):
    return 'LineBottomLeft', (tip + 20, y0, x0 + 8 - (tip + 20), yc + 8 - y0)

def top_right(x0, y0, yc, tip):
    return 'LineTopRight', (x0 - 8, yc - 8, tip - 20 - (x0 - 8), y0 - (yc - 8))

def bottom_right_top(x0, y0, yc, x1):    # same-row jobs: the tip is fixed 13 below the start
    return 'LineBottomRightTop', (x0 - 8, y0 + 33, x1 + 8 - (x0 - 8), yc + 8 - (y0 + 33))

LINES = {
    # Dragoon, now at (200, 850)
    'LineThiefDragoon': bottom(232, 684, 828),
    'LineDragoonDancer': top_right(238, 866, 796, 586),
    'LineDragoonSamurai': bottom_right_top(222, 949, 992, 844),
    'LineDragoonMime': bottom_right_top(242, 949, 1020, 1044),
    # Dark Knight at (404, 850)
    'LineDragoonDarkKnight': right(264, 937, 382),
    'LineNinjaDarkKnight': bottom(436, 684, 828),
    'LineSamuraiDarkKnight': left(828, 935, 488),
    # Onion Knight at (812, 280)
    'LineSquireOnionKnight': right_bottom(440, 150, 836, 258),
    'LineChemistOnionKnight': left_bottom(1458, 150, 852, 258),
}

# lines no stretchable component has: polylines (axis-aligned segments; the last point is the arrow tip), each drawn
# by a component of its own made of the atlas's bar, rounded-corner and arrow pieces (see polyline below)
PATHS = {
    # vanilla's runs straight through Onion Knight's base; this one dips under it
    'LineKnightSamurai': [(672, 372), (760, 372), (760, 428), (974, 428), (974, 938), (892, 938)],
    'LineKnightDarkKnight': [(620, 367), (540, 367), (540, 875), (488, 875)],
    'LineGeomancerDarkKnight': [(828, 707), (560, 707), (560, 905), (488, 905)],
    'LineBlackDarkKnight': [(1680, 372), (1760, 372), (1760, 978), (436, 978), (436, 940)],
}

# per-line labels (generaljob position type 7): top-left of the 40x20 box, absolute; placed on the line near its start
LABELS = {
    'LvLnDragoonSamurai': ('Dragoon', 280, 982),
    'LvLnDragoonMime': ('Dragoon', 340, 1010),
    'LvLnGeomancerDarkKnight': ('Geomancer', 690, 697),
    'LvLnSquireOnionKnight': ('Squire', 500, 140),
    'LvLnChemistOnionKnight': ('Chemist', 1360, 140),
}

def build(src_root, out_root):
    u = Uib(os.path.join(src_root, PATH))
    tree = u.find('JobTree')
    root = next(n for n in u.node_list(tree['nodes'], tree['node_count']) if n['name'] == 'LayerRoot')
    jobs = {c['name']: c for c in root['children']}
    assert 'Mime' in jobs and not any(n in jobs for n, _, _ in NEW_NODES), list(jobs)

    u.move_node(jobs['Dragoon'], *DRAGOON)
    for name, x, y in NEW_NODES:
        u.add_child(root, jobs['Knight'], name, x, y)
    jobs = {c['name']: u.node(c['base']) for c in root['children']}

    branches = jobs['LayerBranches']
    templates = {c['ref']: c['base'] for c in reversed(branches['children']) if c.get('ref')}
    u.remove_children(branches, REMOVED_LINES)
    for name, line in LINES.items():
        component, (x, y, w, h), *flip = line
        assert w > 0 and h > 0, (name, w, h)
        u.copy_node(templates[component], branches, name, x, y, w, h, sy=flip[0] if flip else None)

    u.grow_components(len(PATHS))
    for name, points in PATHS.items():
        component, (x, y, w, h) = polyline(u, 'Path' + name[4:], points)
        node = u.copy_node(templates['LineRight'], branches, name, x, y, w, h)
        ref = u.add_string(component)
        struct.pack_into('<i', u.d, node + 0x70, ref - node)

    unit_job = u.find('UnitJob')
    unit_root = u.node_list(unit_job['nodes'], unit_job['node_count'])[0]
    label = next(c for c in unit_root['children'] if c['name'] == 'TextBoardJobLvB')
    for name, (job, x, y) in LABELS.items():
        jx, jy = jobs[job]['x'], jobs[job]['y']
        u.copy_node(label['base'], unit_root, name, x - jx, y - (jy + 8))

    out = os.path.join(out_root, PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    u.save(out)
    return out

# atlas parts (ui_job_tree_uitx.utexpt): corners are the quadrants of a rounded square, the 6px stroke on their outer
# edges; ArrowH points right, ArrowV up (image data flips turn them)
CORNER_LB, CORNER_RB, CORNER_LT, CORNER_RT, ARROW_H, ARROW_V, MIDDLE_H, MIDDLE_V = 2, 3, 4, 5, 6, 7, 9, 10
STROKE, CORNER, ARROW = 6, 16, 20
# corner part and its box offset from the turn point, by (direction in, direction out); directions as (dx, dy)
TURNS = {
    ((1, 0), (0, 1)): (CORNER_RB, -13, -3), ((0, -1), (-1, 0)): (CORNER_RB, -13, -3),
    ((-1, 0), (0, 1)): (CORNER_LB, -3, -3), ((0, -1), (1, 0)): (CORNER_LB, -3, -3),
    ((-1, 0), (0, -1)): (CORNER_LT, -3, -13), ((0, 1), (1, 0)): (CORNER_LT, -3, -13),
    ((1, 0), (0, -1)): (CORNER_RT, -13, -13), ((0, 1), (-1, 0)): (CORNER_RT, -13, -13),
}

def polyline(u, name, points):
    """Adds component `name` drawing the polyline (bars, rounded corners, arrow at the last point); returns it and
    its box (absolute), where the line node referencing it goes."""
    def direction(a, b):
        return ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))
    dirs = [direction(points[i], points[i + 1]) for i in range(len(points) - 1)]
    assert all(abs(dx) + abs(dy) == 1 for dx, dy in dirs), points
    pieces = []                                   # (source, x, y, w, h, part, flip_x, flip_y), absolute
    hbar, vbar = component_child(u, 'LineRight', 'Image02'), component_child(u, 'LineBottom', 'Image02')
    corner, arrow = component_child(u, 'LineRightBottom', 'Image03'), component_child(u, 'LineRight', 'Image05')
    for i, (a, b) in enumerate(zip(points, points[1:])):
        d = dirs[i]
        start = a if i == 0 else (a[0] + 13 * d[0], a[1] + 13 * d[1])
        last = i == len(dirs) - 1
        trim = ARROW if last else 13
        end = (b[0] - trim * d[0], b[1] - trim * d[1])
        if d[1] == 0:
            xa, xb = sorted((start[0], end[0]))
            pieces.append((hbar, xa, a[1] - 3, xb - xa, STROKE, MIDDLE_H, False, False))
        else:
            ya, yb = sorted((start[1], end[1]))
            pieces.append((vbar, a[0] - 3, ya, STROKE, yb - ya, MIDDLE_V, False, False))
        if not last:
            part, ox, oy = TURNS[(d, dirs[i + 1])]
            pieces.append((corner, b[0] + ox, b[1] + oy, CORNER, CORNER, part, False, False))
    tx, ty = points[-1]
    d = dirs[-1]
    pieces.append({(1, 0): (arrow, tx - 20, ty - 10, ARROW, ARROW, ARROW_H, False, False),
                   (-1, 0): (arrow, tx, ty - 10, ARROW, ARROW, ARROW_H, True, False),
                   (0, -1): (arrow, tx - 10, ty, ARROW, ARROW, ARROW_V, False, False),
                   (0, 1): (arrow, tx - 10, ty - 20, ARROW, ARROW, ARROW_V, False, True)}[d])
    x0 = min(p[1] for p in pieces); y0 = min(p[2] for p in pieces)
    x1 = max(p[1] + p[3] for p in pieces); y1 = max(p[2] + p[4] for p in pieces)
    children = [u.image_piece(src, x - x0, y - y0, w, h, part, fx, fy) for src, x, y, w, h, part, fx, fy in pieces]
    u.add_component(name, 'LineRight', x1 - x0, y1 - y0, children)
    return name, (x0, y0, x1 - x0, y1 - y0)

def component_child(u, component, name):
    c = u.find(component)
    layer = u.node_list(c['nodes'], c['node_count'])[0]
    return next(n['base'] for n in layer['children'] if n['name'] == name)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print('wrote', build(sys.argv[1], sys.argv[2]))
