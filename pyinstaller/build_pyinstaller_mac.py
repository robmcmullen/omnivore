#!/usr/bin/env python
import os
import shutil
from subprocess import Popen, PIPE

execfile("../omnivore/_omnivore_version.py")

from subprocess import Popen, PIPE

def run(args):
    p = Popen(args, stdout=PIPE, bufsize=1)
    with p.stdout:
        for line in iter(p.stdout.readline, b''):
            print line,
    p.wait()

# can't use Omnivore because omnivore is a directory name and the filesystem is
# case-insensitive
build_target="OmnivoreXL"
build_app = "dist/%s.app" % build_target

# target app will be renamed
final_target="Omnivore"
dest_dir = "../dist-%s" % version
final_app = "%s.app" % final_target
dest_app = "%s/%s" % (dest_dir, final_app)
final_zip = "%s-%s-darwin.tbz" % (final_target, version)
dest_zip = "%s/%s" % (dest_dir, final_zip)

print "Building %s" % build_app
run(['pyinstaller', '-y', '--debug', '--windowed', '%s.spec' % build_target])

try:
	os.mkdir(dest_dir)
	print "Creating %s" % dest_dir
except OSError:
	# Directory exists; remove old stuff
	if os.path.exists(dest_app):
		print "Removing old %s" % dest_app
		shutil.rmtree(dest_app)
	if os.path.exists(dest_zip):
		print "Removing old %s" % dest_zip
		os.unlink(dest_zip)

print "Copying %s -> %s & removing architectures other than x86_64" % (build_app, dest_app)
#shutil.copytree(build_app, dest_app, True)
run(['/usr/bin/ditto', '-arch', 'x86_64', build_app, dest_app])

print "Copying new Info.plist"
shutil.copyfile("Info.plist", "%s/Contents/Info.plist" % dest_app)

print "Zipping %s" % dest_zip
run(['tar', 'cfj', dest_zip, '-C', dest_dir, final_app])
