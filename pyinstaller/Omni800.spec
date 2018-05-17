# -*- mode: python -*-

block_cipher = None

with open("../wxatari.py", "r") as fh:
    script = fh.read()
with open("Omni800.py", "w") as fh:
    fh.write(script)

import sys
sys.modules['FixTk'] = None

a = Analysis(['Omni800.py'],
             pathex=['/Users/rob.mcmullen/src/atari800/python'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'Cython', 'sphinx', 'nose', 'pygments'],
             cipher=block_cipher)

for pymod, path, tag in sorted(a.pure):
    if ".qt" in pymod or ".test" in pymod:
        print "why is this still here?", pymod

# pytz zip bundle from https://github.com/pyinstaller/pyinstaller/wiki/Recipe-pytz-zip-file
# DOESN'T WORK ON MAC!

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

if sys.platform == "darwin":
    icon = '../resources/Omni800.icns'
    exe = EXE(pyz,
        a.scripts,
        exclude_binaries=True,
        name='Omni800',
        debug=False,
        strip=True,
        upx=True,
        console=False,
        icon=icon)
    coll = COLLECT(exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=None,
        upx=True,
        name='Omni800')  # dir in dist: ..../dist/Omnivore
    app = BUNDLE(coll,
       name='Omni800.app',
       bundle_identifier="com.playermissile.omni800",
       icon=icon)

elif sys.platform == "win32":
    exe = EXE(pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='Omni800',
        debug=False,
        strip=False,
        upx=True,
        console=False,
        icon="../omnivore/icons/omnivore.ico")


