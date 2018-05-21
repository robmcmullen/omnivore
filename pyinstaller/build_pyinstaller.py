#!/usr/bin/env python
import os
import sys
import shutil
from subprocess import Popen, PIPE

if sys.platform == 'win32':
    # On windows, you can disable installation of egg files by creating the
    # file %HOMEPATH%/pydistutils.cfg
    #
    # pyinstaller 3.2 doesn't work with the 'future' library. Development
    # branch was suggested because of a fix for:
    # https://github.com/pyinstaller/pyinstaller/issues/1935 but it still
    # doesn't work. There are dynamic imports that aren't being included, so I
    # had to create hook-future.py to include those.
    win = True
    mac = False
    exe = ".exe"
elif sys.platform == 'darwin':
    win = False
    mac = True
    exe = ".app"
else:  # linux
    win = False
    mac = False
    exe = ""


exec(compile(open("../omnivore/_omnivore_version.py").read(), "../omnivore/_omnivore_version.py", 'exec'))

from subprocess import Popen, PIPE

def run(args):
    p = Popen(args, stdout=PIPE, bufsize=1)
    with p.stdout:
        for line in iter(p.stdout.readline, b''):
            print(line, end=' ')
    p.wait()

# can't use Omnivore because omnivore is a directory name and the filesystem is
# case-insensitive
build_target="OmnivoreXL"
build_app = "dist/" + build_target + exe

# target app will be renamed
final_target="Omnivore"
dest_dir = "../dist-%s" % version
final_app = final_target + exe
dest_app = "%s/%s" % (dest_dir, final_app)
final_exe = "%s-%s-win.exe" % (final_target, version)
final_zip = "%s-%s-darwin.tbz" % (final_target, version)
dest_exe = "%s/%s" % (dest_dir, final_exe)
dest_zip = "%s/%s" % (dest_dir, final_zip)

print("Building %s" % build_app)
args = ['pyinstaller', '-y']
args.append('%s.spec' % build_target)
run(args)

try:
    os.mkdir(dest_dir)
    print("Creating %s" % dest_dir)
except OSError:
    # Directory exists; remove old stuff
    if os.path.exists(dest_app):
        print("Removing old %s" % dest_app)
        shutil.rmtree(dest_app)
    if os.path.exists(dest_zip):
        print("Removing old %s" % dest_zip)
        os.unlink(dest_zip)
    if os.path.exists(dest_app):
        print("Removing old %s" % dest_exe)
        shutil.rmtree(dest_exe)

if win:
    print("Copying %s -> %s" % (build_app, dest_exe))
    shutil.copyfile(build_app, dest_exe)
elif mac:
    print("Copying %s -> %s & removing architectures other than x86_64" % (build_app, dest_app))
    #shutil.copytree(build_app, dest_app, True)
    run(['/usr/bin/ditto', '-arch', 'x86_64', build_app, dest_app])

    print("Copying new Info.plist")
    with open("Info.plist", "r") as fh:
        text = fh.read()
    text = text.format(version=version)
    with open("%s/Contents/Info.plist" % dest_app, "w") as fh:
        fh.write(text)

    print("Signing (with self-signed cert)")
    run(["codesign", "-s", "Player/Missile Podcast", "--deep", dest_app])

    print("Zipping %s" % dest_zip)
    run(['tar', 'cfj', dest_zip, '-C', dest_dir, final_app])
