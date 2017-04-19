# -*- mode: python -*-

block_cipher = None

with open("../run.py", "r") as fh:
  script = fh.read()
with open("Omnivore.py", "w") as fh:
  fh.write(script)

a = Analysis(['Omnivore.py'],
             pathex=['N:\\maproom-deps\\omnivore'],
             binaries=[],
             datas=[
                 ('../omnivore8bit/templates/*', 'omnivore8bit/templates'),
                 ('../omnivore8bit/help/*', 'omnivore8bit/help'),
                 ('../omnivore8bit/help/_static/*', 'omnivore8bit/help/_static'),
                 ('../omnivore8bit/help/_images/*', 'omnivore8bit/help/_images'),
             ],
             hiddenimports=['omnivore8bit'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'Cython', 'traits.tests', 'traits.adaptation.tests', 'traits.etsconfig.tests', 'traits.testing.tests', 'traits.util.tests', 'traitsui.tests', 'traitsui.qt4', 'pyface.qt', 'pyface.ui.qt4', 'pyface.ui.null', 'pyface.tests', 'pyface.ui.wx.tests', 'pyface.ui.wx.grid.tests', 'pyface.util.tests', 'pyface.tasks.tests', 'pyface.action.tests', 'pyface.workbench.tests', 'envisage.tests'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

# Find any test directories
s = set()
for p, _, _ in a.pure:
    s.add(p)
tests = sorted([n for n in s if ".tests" in n])
print "\n".join(tests)

# pytz zip bundle from https://github.com/pyinstaller/pyinstaller/wiki/Recipe-pytz-zip-file

from pytz_zip import pytz_zip
pytz_zip ( a )

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Omnivore',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Omnivore')
