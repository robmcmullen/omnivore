#!/usr/bin/env python
"""

"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

DEBUG=False

subpkgs = [
    "traits",
    "traitsui",
    "pyface",
    "omnivore",
    "omnivore8bit"
]

hiddenimports = []
skipped = []
for s in subpkgs:
    possible = collect_submodules(s)
    for pymod in possible:
        if ".tests" in pymod or ".qt" in pymod or ".null" in pymod:
            skipped.append(pymod)
        else:
            hiddenimports.append(pymod)

if DEBUG or True:
    print "\n".join(sorted(hiddenimports))
    print "SKIPPED:"
    print "\n".join(sorted(skipped))

subpkgs = [
    "traitsui",
    "pyface",
    "omnivore",
    "omnivore8bit"
]
datas = []
skipped = []
for s in subpkgs:
    possible = collect_data_files(s)
    # Filter out stuff.  Handle / and \ for path separators!
    for src, dest in possible:
        if "/qt" not in src and "\\qt" not in src and (".jpg" in src or ".png" in src or ".ico" in src or ".zip" in src):
            datas.append((src, dest))
        elif ("omnivore/omnivore" in src or "omnivore\\omnivore" in src) and ("/help" in src or "/templates" in src or "\\help" in src or "\\templates" in src or ".jpg" in src or ".png" in src or ".ico" in src):
            datas.append((src, dest))
        else:
            skipped.append((src, dest))

if DEBUG:
    print "\n".join(["%s -> %s" % d for d in datas])
    print "SKIPPED:"
    print "\n".join(["%s -> %s" % d for d in skipped])
