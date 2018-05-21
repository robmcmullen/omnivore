# -*- mode: python -*-

block_cipher = None
DEBUG = False

with open("../run.py", "r") as fh:
    script = fh.read()
with open("OmnivoreXL.py", "w") as fh:
    fh.write(script)

import sys
sys.modules['FixTk'] = None

if sys.platform == "darwin":
    pathex = ['/Users/rob.mcmullen/src/omnivore']
elif sys.platform == "win32":
    pathex = ['S:/omnivore']

a = Analysis(['OmnivoreXL.py'],
             pathex=pathex,
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'Cython', 'sphinx', 'nose', 'pygments'],
             cipher=block_cipher)

for pymod, path, tag in sorted(a.pure):
    if ".qt" in pymod or ".test" in pymod:
        print("why is this still here?", pymod)

# pytz zip bundle from https://github.com/pyinstaller/pyinstaller/wiki/Recipe-pytz-zip-file
# DOESN'T WORK ON MAC!

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

if sys.platform == "darwin":
    icon = '../resources/omnivore.icns'
    exe = EXE(pyz,
        a.scripts,
        exclude_binaries=True,
        name='OmnivoreXL',
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
        name='OmnivoreXL')  # dir in dist: ..../dist/Omnivore
    app = BUNDLE(coll,
       name='OmnivoreXL.app',
       bundle_identifier="com.playermissile.omnivore",
       icon=icon)

elif sys.platform == "win32":
    upx = not DEBUG
    console = DEBUG
    exe = EXE(pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='OmnivoreXL',
        debug=DEBUG,
        strip=False,
        upx=upx,
        console=console,
        icon="../omnivore/icons/omnivore.ico")


