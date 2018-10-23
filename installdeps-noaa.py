#!/usr/bin/env python
import subprocess
import os
import sys

from installdeps import install_update_deps


deps = [
    ['git@github.com:robmcmullen/GnomeTools.git', {'builddir': 'post_gnome', 'branch': 'py3'}, False],
    ['https://github.com/fathat/glsvg.git', {}, False],
    ['https://github.com/robmcmullen/pyugrid.git', {}, False],
    ['git@github.com:robmcmullen/pyface.git', {'branch': 'wx4may2018'}, True],
    ['git@github.com:robmcmullen/traitsui.git', {'branch': 'wx4may2018'}, True],
    ['https://github.com/enthought/apptools.git', {}, True],
    ['git@github.com:robmcmullen/envisage.git', {}, False],
]

link_map = {
    "GnomeTools": "post_gnome",
}

if __name__ == "__main__":
    install_update_deps(deps, link_map)
