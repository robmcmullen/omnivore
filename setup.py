import os
import sys
from setuptools import setup, find_packages, Extension
import numpy as np

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS", "/Zi"]
    extra_link_args=['/DEBUG']
    config_include = "libatari800/include/win"
else:
    # extra_compile_args = ["-g", "-O3"]
    extra_compile_args = ["-O3"]
    extra_link_args = []
    config_include = "libatari800/include/linux"

extensions = [
  Extension("omni8bit.atari800.libatari800",
    sources = ["libatari800/libatari800.c",
    "libatari800/atari800/src/libatari800/main.c",
    "libatari800/atari800/src/libatari800/input.c",
    "libatari800/atari800/src/libatari800/video.c",
    "libatari800/atari800/src/libatari800/init.c",
    "libatari800/atari800/src/libatari800/sound.c",
    "libatari800/atari800/src/libatari800/statesav.c",
    "libatari800/atari800/src/afile.c",
    "libatari800/atari800/src/antic.c",
    "libatari800/atari800/src/atari.c",
    "libatari800/atari800/src/binload.c",
    "libatari800/atari800/src/cartridge.c",
    "libatari800/atari800/src/cassette.c",
    "libatari800/atari800/src/compfile.c",
    "libatari800/atari800/src/cfg.c",
    "libatari800/atari800/src/cpu.c",
    "libatari800/atari800/src/crc32.c",
    "libatari800/atari800/src/devices.c",
    "libatari800/atari800/src/emuos_altirra.c",
    "libatari800/atari800/src/esc.c",
    "libatari800/atari800/src/gtia.c",
    "libatari800/atari800/src/img_tape.c",
    "libatari800/atari800/src/log.c",
    "libatari800/atari800/src/memory.c",
    "libatari800/atari800/src/monitor.c",
    "libatari800/atari800/src/pbi.c",
    "libatari800/atari800/src/pia.c",
    "libatari800/atari800/src/pokey.c",
    "libatari800/atari800/src/rtime.c",
    "libatari800/atari800/src/sio.c",
    "libatari800/atari800/src/sysrom.c",
    "libatari800/atari800/src/util.c",
    "libatari800/atari800/src/input.c",
    "libatari800/atari800/src/statesav.c",
    "libatari800/atari800/src/ui_basic.c",
    "libatari800/atari800/src/ui.c",
    "libatari800/atari800/src/artifact.c",
    "libatari800/atari800/src/colours.c",
    "libatari800/atari800/src/colours_ntsc.c",
    "libatari800/atari800/src/colours_pal.c",
    "libatari800/atari800/src/colours_external.c",
    "libatari800/atari800/src/screen.c",
    "libatari800/atari800/src/cycle_map.c",
    "libatari800/atari800/src/pbi_mio.c",
    "libatari800/atari800/src/pbi_bb.c",
    "libatari800/atari800/src/pbi_scsi.c",
    "libatari800/atari800/src/pokeysnd.c",
    "libatari800/atari800/src/mzpokeysnd.c",
    "libatari800/atari800/src/remez.c",
    "libatari800/atari800/src/sndsave.c",
    "libatari800/atari800/src/sound.c",
    "libatari800/atari800/src/pbi_xld.c",
    "libatari800/atari800/src/voicebox.c",
    "libatari800/atari800/src/votrax.c",
    "libatari800/atari800/src/votraxsnd.c",
              ],
    extra_compile_args = extra_compile_args,
    extra_link_args = extra_link_args,
    include_dirs = [config_include, "libatari800/atari800/src", "libatari800/atari800/src/libatari800", np.get_include()],
    undef_macros = [ "NDEBUG" ],
    )
]

cmdclass = dict()

# Cython is only used when creating a source distribution. Users don't need
# to install Cython unless they are modifying the .pyx files themselves.
if "sdist" in sys.argv:
    try:
        from Cython.Build import cythonize
        from distutils.command.sdist import sdist as _sdist

        class sdist(_sdist):
            def run(self):
                cythonize(["libatari800/libatari800.pyx"], gdb_debug=True)
                _sdist.run(self)
        cmdclass["sdist"] = sdist
    except ImportError:
        # assume the user doesn't have Cython and hope that the C file
        # is included in the source distribution.
        pass

execfile('omni8bit/_metadata.py')

setup(
    name = "omni8bit",
    version = __version__,
    author = __author__,
    author_email = __author_email__,
    url = __url__,
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
    """.splitlines() if len(c.strip()) > 0],
    description = "Unified front-end providing common interface to control several 8 bit emulators",
    long_description = open('README.rst').read(),
    cmdclass = cmdclass,
    ext_modules = extensions,
    packages = ["omni8bit"],
    install_requires = [
    'numpy',
    'pyopengl',
    'pyopengl_accelerate',
    'pillow',
    'construct<2.9',  # Construct 2.9 changed the String class
    ],
)
