#!/usr/bin/env python
"""

"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

subpkgs = [
    "traits",
    "traitsui",
    "pyface",
    "omnivore",
]

hiddenimports = []
for s in subpkgs:
    hiddenimports.extend(collect_submodules(s))
#print hiddenimports

subpkgs = [
    "traitsui",
    "pyface",
    "omnivore",
]
datas = []
for s in subpkgs:
    datas.extend(collect_data_files(s))
#print datas
