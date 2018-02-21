# setup file for only the framework part of Omnivore. Includes:
#
# Enthought (traits, traitsui, pyface, apptools, envisage)
# pyfilesystem
# 
# Doesn't include:
#
# omnivore8bit
# omnivore_extra
# udis
#
import os
import sys
import shutil
import glob
import subprocess
from setuptools import find_packages
from setuptools import setup
from distutils.extension import Extension

ext_modules = [
    Extension("traits.ctraits",
              sources = ["traits/ctraits.c"],
              extra_compile_args = ["-DNDEBUG=1", "-O3" ]#, '-DPy_LIMITED_API'],
              ),
    ]

install_requires = [
    'numpy',
    'jsonpickle>=0.9.4',
    'bson<1.0.0',
    'configobj',
    'pyparsing',
    ]


cmdclass = dict()

import omnivore
full_version = "1.0rc14"
spaceless_version = full_version.replace(" ", "_")

common_includes = [
    "ctypes",
    "ctypes.util",
    "wx.lib.pubsub.*",
    "wx.lib.pubsub.core.*",
    "wx.lib.pubsub.core.kwargs.*",
    "multiprocessing",
    "pkg_resources",
    "configobj",
    
    "traits",
    
    "traitsui",
    "traitsui.editors",
    "traitsui.editors.*",
    "traitsui.extras",
    "traitsui.extras.*",
    "traitsui.wx",
    "traitsui.wx.*",
 
    "pyface",
    "pyface.*",
    "pyface.wx",
 
    "pyface.ui.wx",
    "pyface.ui.wx.init",
    "pyface.ui.wx.*",
    "pyface.ui.wx.grid.*",
    "pyface.ui.wx.action.*",
    "pyface.ui.wx.timer.*",
    "pyface.ui.wx.tasks.*",
    "pyface.ui.wx.workbench.*",
]
common_includes.extend(omnivore.get_py2exe_toolkit_includes())

py2app_includes = [
]

common_excludes = [
    "test",
#    "unittest", # needed for numpy
    "pydoc_data",
    "pyface.ui.qt4",
    "traitsui.qt4",
     "Tkconstants",
    "Tkinter", 
    "tcl", 
    "_imagingtk",
    "PIL._imagingtk",
    "ImageTk",
    "PIL.ImageTk",
    "FixTk",
    ]

py2exe_excludes = [
    ]

# package_data is for pip and python installs, not for app bundles. Need
# to use data_files for that
package_data = {
    '': ['images/*',
         '*.ini',
         ],
    'apptools': ['help/help_plugin/*.ini',
                 'help/help_plugin/action/images/*.png',
                 'logger/plugin/*.ini',
                 'logger/plugin/view/images/*.png',
                 'naming/ui/images/*.png',
                 ],
    'traitsui': ['image/library/*.zip',
                 'wx/images/*',
                 'qt4/images/*',
                 ],
    'pyface': ['image/library/*.zip',
               'images/*',
               'dock/images/*',
               'tree/images/*',
               'tests/images/*',
               'action/images/*',
               'ui/wx/images/*',
               'ui/wx/grid/images/*',
               ],
    'omnivore': ['icons/*.png',
                 'icons/*.ico',
                 'utils/*.png',
                 'templates/*',
                 ],
    }

all_packages = find_packages()

# cull packages
packages = []
for p in all_packages:
    if p.startswith("omnivore8bit") or p.startswith("omnivore_extra") or p.startswith("udis"):
        continue
    packages.append(p)

base_dist_dir = "dist-%s" % spaceless_version
win_dist_dir = os.path.join(base_dist_dir, "win")
mac_dist_dir = os.path.join(base_dist_dir, "mac")

is_64bit = sys.maxsize > 2**32

options = {}

# data files are only needed when building an app bundle
data_files = []

setup(
    name = 'omnivore-framework',
    version = full_version,
    author = omnivore.__author__,
    author_email = omnivore.__author_email__,
    url = omnivore.__url__,
    download_url = ('%s/%s.tar.gz' % (omnivore.__download_url__, full_version)),
    classifiers = [c.strip() for c in """\
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        License :: OSI Approved :: GNU General Public License (GPL)
        Operating System :: MacOS
        Operating System :: Microsoft :: Windows
        Operating System :: OS Independent
        Operating System :: POSIX
        Operating System :: Unix
        Programming Language :: Python
        Topic :: Utilities
        Topic :: Software Development :: Assemblers
        Topic :: Software Development :: Disassemblers
        """.splitlines() if len(c.strip()) > 0],
    description = "Traits-based wxPython UI application framework",
    long_description = open('README.rst').read(),
    cmdclass = cmdclass,
    ext_modules = ext_modules,
    install_requires = install_requires,
    setup_requires = ["numpy"],
    license = "GPL",
    packages = packages,
    package_data = package_data,
    data_files=data_files,
    entry_points = {
          'pyface.toolkits': [
              'wx = pyface.ui.wx.init:toolkit_object',
              'null = pyface.ui.null.init:toolkit_object',
          ],
    },
    options=options,
    platforms = ["Windows", "Linux", "Mac OS-X", "Unix"],
    zip_safe = False,
    )
