# Copyright (c) 2008-2013 by Enthought, Inc.
# All rights reserved.
from os.path import join
from setuptools import setup, find_packages
from distutils.extension import Extension
from Cython.Distutils import build_ext

import numpy


info = {}
execfile(join('omnimon', '__init__.py'), info)

ext_modules = [
    Extension("omnimon.utils.wx.bitviewscroller_speedups",
              sources=["omnimon/utils/wx/bitviewscroller_speedups.pyx"],
              include_dirs=[numpy.get_include()],
              ),
    ]

setup(
    name = 'omnimon',
    version = info['__version__'],
    author = info['__author__'],
    author_email = info['__author_email__'],
    url = info['__url__'],
    download_url = ('%s-%s.tar.gz' % (info['__download_url__'], info['__version__'])),
    classifiers = [c.strip() for c in """\
        Development Status :: 3 - Alpha
        Intended Audience :: Developers
        License :: OSI Approved :: GNU General Public License (GPL)
        Operating System :: MacOS
        Operating System :: Microsoft :: Windows
        Operating System :: OS Independent
        Operating System :: POSIX
        Operating System :: Unix
        Programming Language :: Python
        Topic :: Software Development :: Libraries
        Topic :: Text Editors
        """.splitlines() if len(c.strip()) > 0],
    description = '(ap)Proximated (X)Emacs Powered by Python.',
    long_description = open('README.rst').read(),
    cmdclass={'build_ext': build_ext},
    ext_modules = ext_modules,
    install_requires = info['__requires__'],
    license = "BSD",
    packages = find_packages(),
    package_data = {'': ['images/*', '*.ini',]},
    platforms = ["Windows", "Linux", "Mac OS-X", "Unix", "Solaris"],
    zip_safe = False,
)
