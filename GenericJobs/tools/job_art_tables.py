"""Registers Dark Knight's and Onion Knight's job sheet art (job_visual jv_21 / jv_22) in the nxd tables.

  python tools/job_art_tables.py <vanilla nxd dir> <mod nxd dir>      (needs FF16Tools.CLI; FF16TOOLS overrides its path)

The vanilla dir needs the game's current icon.nxd and jobtype.nxd (both in data/enhanced/0004.pac); the mod dir is
the mod's FFTIVC/data/enhanced/nxd, whose job.{de,en,fr,ja}.nxd are edited in place and where icon.nxd and
jobtype.nxd are written.

How the art is found: Job.jobtype+Id -> JobType row (MaleVisualIconId / FemaleVisualIconId, picked by the unit's
gender; its only reader is 0x1400FBEB8) -> Icon row (IconFilePath, relative to ui/ffto/icon/). Vanilla's job art is
Icon 701-719 (male) / 720-738 (female); 739 on are blank. Dark Knight used JobType 21, the Templar's (no art), and
Onion Knight 0 (no row), so they get unused JobType rows 115 / 116.
"""
import os, shutil, sqlite3, subprocess, sys, tempfile

FF16TOOLS = os.environ.get('FF16TOOLS', r'H:\FFT\win-x64\FF16Tools.CLI.exe')
LANGS = ['de', 'en', 'fr', 'ja']

DARK_KNIGHT, ONION_KNIGHT = 160, 161
JOB_TYPES = {DARK_KNIGHT: 115, ONION_KNIGHT: 116}
ICONS = {  # icon id: path; (male, female) per job
    739: 'job_visual/textureparts/jv_21_m_uitx.utexpt', 740: 'job_visual/textureparts/jv_21_f_uitx.utexpt',
    741: 'job_visual/textureparts/jv_22_m_uitx.utexpt', 742: 'job_visual/textureparts/jv_22_f_uitx.utexpt',
}
VISUALS = {DARK_KNIGHT: (739, 740), ONION_KNIGHT: (741, 742)}

def run(*args):
    subprocess.run([FF16TOOLS, *args, '-g', 'fft'], check=True, capture_output=True)

def edit(src_files, out_dir, change):
    """nxd -> sqlite, change(connection), sqlite -> nxd, for the given nxd files."""
    work = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(work, 'in'))
        for f in src_files: shutil.copy(f, os.path.join(work, 'in'))
        db = os.path.join(work, 'tables.sqlite')
        run('nxd-to-sqlite', '-i', os.path.join(work, 'in'), '-o', db)
        c = sqlite3.connect(db); change(c); c.commit(); c.close()
        run('sqlite-to-nxd', '-i', db, '-o', os.path.join(work, 'out'))
        names = {os.path.basename(f) for f in src_files}
        for root, _, files in os.walk(os.path.join(work, 'out')):
            for f in files:
                if f in names:
                    shutil.copy(os.path.join(root, f), os.path.join(out_dir, f)); names.discard(f)
        assert not names, names
    finally:
        shutil.rmtree(work, ignore_errors=True)

def tables(src_dir, out_dir):
    def icons(c):
        for key, path in ICONS.items():
            assert c.execute('select IconFilePath from Icon where Key = ?', (key,)).fetchone()[0] is None, key
            c.execute('update Icon set IconFilePath = ? where Key = ?', (path, key))
    edit([os.path.join(src_dir, 'icon.nxd')], out_dir, icons)

    def job_types(c):
        for job, job_type in JOB_TYPES.items():
            assert c.execute('select MaleVisualIconId, FemaleVisualIconId from JobType where Key = ?',
                             (job_type,)).fetchone() == (0, 0), job_type
            male, female = VISUALS[job]
            c.execute('update JobType set MaleVisualIconId = ?, FemaleVisualIconId = ? where Key = ?',
                      (male, female, job_type))
    edit([os.path.join(src_dir, 'jobtype.nxd')], out_dir, job_types)

    def jobs(c):
        for lang in LANGS:
            for job, job_type in JOB_TYPES.items():
                c.execute('update "Job-%s" set "jobtype+Id" = ? where Key = ?' % lang, (job_type, job))
    edit([os.path.join(out_dir, 'job.%s.nxd' % lang) for lang in LANGS], out_dir, jobs)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    tables(sys.argv[1], sys.argv[2])
    print('wrote icon.nxd, jobtype.nxd and job.{%s}.nxd in %s' % (','.join(LANGS), sys.argv[2]))
