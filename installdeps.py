#!/usr/bin/env python
import subprocess
import os
import sys

if sys.platform.startswith("win"):
    develop_instead_of_link = True
else:
    develop_instead_of_link = False

deps = [
    ['git@github.com:robmcmullen/traits.git',],
    ['git@github.com:robmcmullen/pyface.git', {'branch': 'wx4may2018'}],
    ['git@github.com:robmcmullen/traitsui.git', {'branch': 'wx4may2018'}],
    ['https://github.com/enthought/apptools.git',],
    ['git@github.com:robmcmullen/envisage.git',],
    ['git@github.com:robmcmullen/pyfilesystem.git', {'branch': 'py3'}],
]


real_call = subprocess.call
def git(args, branch=None):
    real_args = ['git']
    real_args.extend(args)
    real_call(real_args)

dry_run = False
if dry_run:
    def dry_run_call(args):
        print("in %s: %s" % (os.getcwd(), " ".join(args)))
    subprocess.call = dry_run_call
    def dry_run_symlink(source, name):
        print("in %s: %s -> %s" % (os.getcwd(), name, source))
    os.symlink = dry_run_symlink

setup = "python setup.py "

link_map = {
    "pyfilesystem": "fs",
}

linkdir = os.getcwd()
topdir = os.path.join(os.getcwd(), "deps")

for dep in deps:
    os.chdir(topdir)
    try:
        repourl, options = dep
    except ValueError:
        repourl = dep[0]
        options = {}
    print dep, repourl, options
    if repourl.startswith("http") or repourl.startswith("git@"):
        print "UPDATING %s" % repourl
        _, repo = os.path.split(repourl)
        repodir, _ = os.path.splitext(repo)
        if os.path.exists(repodir):
            os.chdir(repodir)
            git(['pull'])
        else:
            git(['clone', repourl])
    else:
        repodir = repourl

    builddir = options.get('builddir', ".")

    command = options.get('command',
        setup + "build_ext --inplace")
    link = repodir
    if "install" in command:
        link = None
    else:
        link = repodir
    if command:
        os.chdir(topdir)
        os.chdir(repodir)
        if 'branch' in options:
            git(['checkout', options['branch']])
        os.chdir(builddir)
        subprocess.call(command.split())
        if "install" not in command and develop_instead_of_link:
            subprocess.call(["python", "setup.py", "develop"])

    if link and sys.platform != "win32":
        os.chdir(linkdir)
        name = link_map.get(repodir, repodir)
        if name is None:
            print("No link for %s" % repodir)
        else:
            src = os.path.normpath(os.path.join("deps", repodir, builddir, name))
            if os.path.islink(name):
                os.unlink(name)
            os.symlink(src, name)
