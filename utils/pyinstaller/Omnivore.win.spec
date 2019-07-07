# -*- mode: python -*-

block_cipher = None

with open("../run.py", "r") as fh:
  script = fh.read()
with open("Omnivore.py", "w") as fh:
  fh.write(script)

a = Analysis(['Omnivore.py'],
             pathex=['S:\\omnivore'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'Cython'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

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
