"""Job tree navigation and requirement lines for Dark Knight (slot 20) and Onion Knight (slot 21), plus Dragoon, which
moves under Thief (see jobtree_layout.py), in generaljob.nxd.

  python tools/generaljob_tree.py <the mod's original generaljob.nxd> <output dir>
  (needs FF16Tools.CLI; FF16TOOLS overrides its path. Run it on the original: vanilla's "none" (20) is rewritten.)

generaljob (nxd 189) row = job slot (0-19 Squire..Mime, 20 Dark Knight, 21 Onion Knight).
- Unknown28..44 are each node's cursor neighbours in 8 directions (0 right, 1 down-right, 2 down, 3 down-left, 4 left,
  5 up-left, 6 up, 7 up-right), Unknown48..64 a fallback per direction (used when the first is the other gender's
  Bard/Dancer). Vanilla marks "no neighbour" with 20, which the mod's tree patch makes a real node (Dark Knight), so
  every 20 becomes 255, a value the game already treats as none.
- RequiredJobIds / RequiredJobLevels / RequiredJobPositions: one line per requirement; the position is the label
  (1 left, 2 right, 3 bottom, 4 top box of the required job; 5/6 a shared "Lv" line; 7 the line's own label, through
  the mod's hook). A requirement without a position gets no line.
"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile

FF16TOOLS = os.environ.get('FF16TOOLS', r'H:\FFT\win-x64\FF16Tools.CLI.exe')
NONE = 255
DK, OK = 20, 21
PRIMARY = ['Unknown%X' % (0x28 + 4 * d) for d in range(8)]
FALLBACK = ['Unknown%X' % (0x48 + 4 * d) for d in range(8)]
RIGHT, DOWN_RIGHT, DOWN, DOWN_LEFT, LEFT, UP_LEFT, UP, UP_RIGHT = range(8)
SQUIRE, CHEMIST, KNIGHT, ARCHER, MONK, WHITE, BLACK, TIME, SUMMONER, THIEF, ORATOR, MYSTIC, GEOMANCER, DRAGOON,     SAMURAI, NINJA, ARITHMETICIAN, BARD, DANCER, MIME = range(20)
L, R, B, T, OWN = 1, 2, 3, 4, 7

# cursor neighbours: (row, column, value)
EDITS = [
    # Onion Knight, right of Knight: Knight <-> Onion Knight <-> White Mage
    (OK, PRIMARY[RIGHT], WHITE), (OK, PRIMARY[DOWN], GEOMANCER), (OK, PRIMARY[DOWN_LEFT], MONK), (OK, PRIMARY[LEFT], KNIGHT),
    (OK, PRIMARY[UP_LEFT], SQUIRE), (OK, PRIMARY[UP], SQUIRE), (OK, PRIMARY[UP_RIGHT], CHEMIST),
    (KNIGHT, PRIMARY[RIGHT], OK), (WHITE, PRIMARY[LEFT], OK),
    # Dragoon, now under Thief at (200, 850): Thief / Dragoon / Dark Knight / Samurai / Mime along the bottom row
    (DRAGOON, PRIMARY[RIGHT], DK), (DRAGOON, PRIMARY[DOWN_RIGHT], NONE), (DRAGOON, PRIMARY[DOWN], ARCHER),
    (DRAGOON, PRIMARY[UP_LEFT], NONE), (DRAGOON, PRIMARY[UP], THIEF), (DRAGOON, FALLBACK[UP], NONE),
    (DRAGOON, PRIMARY[UP_RIGHT], NINJA),
    (THIEF, PRIMARY[DOWN_RIGHT], DK), (THIEF, PRIMARY[DOWN], DRAGOON),
    # Dark Knight in Dragoon's old place (404, 850)
    (DK, PRIMARY[RIGHT], SAMURAI), (DK, PRIMARY[DOWN], SQUIRE), (DK, PRIMARY[LEFT], DRAGOON),
    (DK, PRIMARY[UP_LEFT], THIEF), (DK, PRIMARY[UP], NINJA), (DK, PRIMARY[UP_RIGHT], DANCER),
    (DK, FALLBACK[UP_RIGHT], GEOMANCER),
    (NINJA, PRIMARY[DOWN], DK), (NINJA, PRIMARY[DOWN_LEFT], DRAGOON),
    (SAMURAI, PRIMARY[LEFT], DK), (DANCER, PRIMARY[DOWN], DK), (DANCER, PRIMARY[DOWN_LEFT], DK), (DANCER, PRIMARY[LEFT], DK),
    (GEOMANCER, PRIMARY[DOWN_LEFT], DK), (SQUIRE, PRIMARY[UP], DK),
]

# requirement line labels: row -> {required job: position}; everything else keeps the mod's/vanilla's
POSITIONS = {
    SAMURAI: {DRAGOON: OWN},
    MIME: {DRAGOON: OWN},
    DK: {KNIGHT: L, BLACK: R, GEOMANCER: OWN, DRAGOON: R, SAMURAI: L, NINJA: B},
    OK: {SQUIRE: OWN, CHEMIST: OWN},
}

def build(src, out_dir):
    work = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(work, 'in'))
        shutil.copy(src, os.path.join(work, 'in', 'generaljob.nxd'))
        db = os.path.join(work, 'generaljob.sqlite')
        subprocess.run([FF16TOOLS, 'nxd-to-sqlite', '-i', os.path.join(work, 'in'), '-o', db, '-g', 'fft'],
                       check=True, capture_output=True)
        c = sqlite3.connect(db)
        keys = [k for (k,) in c.execute('select Key from GeneralJob order by Key')]
        assert keys == list(range(22)), keys
        for col in PRIMARY + FALLBACK:
            c.execute('update GeneralJob set %s = ? where %s = 20' % (col, col), (NONE,))
        for row, col, value in EDITS:
            c.execute('update GeneralJob set %s = ? where Key = ?' % col, (value, row))
        for row, wanted in POSITIONS.items():
            ids, positions = c.execute('select RequiredJobIds, RequiredJobPositions from GeneralJob where Key = ?',
                                       (row,)).fetchone()
            ids, positions = json.loads(ids), json.loads(positions)
            positions += [0] * (len(ids) - len(positions))
            for job, position in wanted.items():
                positions[ids.index(job)] = position
            assert all(positions), (row, positions)
            c.execute('update GeneralJob set RequiredJobPositions = ? where Key = ?',
                      (json.dumps(positions, separators=(',', ':')), row))
        c.commit(); c.close()
        subprocess.run([FF16TOOLS, 'sqlite-to-nxd', '-i', db, '-o', os.path.join(work, 'out'), '-g', 'fft'],
                       check=True, capture_output=True)
        os.makedirs(out_dir, exist_ok=True)
        got = [os.path.join(r, f) for r, _, fs in os.walk(os.path.join(work, 'out')) for f in fs if f == 'generaljob.nxd']
        assert len(got) == 1, got
        shutil.copy(got[0], os.path.join(out_dir, 'generaljob.nxd'))
        return os.path.join(out_dir, 'generaljob.nxd')
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print('wrote', build(sys.argv[1], sys.argv[2]))
