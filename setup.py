import os
import sys
from setuptools import setup, find_packages, Extension
import numpy as np

if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS", "/Zi"]
    extra_link_args=['/DEBUG']
    libatari800_config_include = "libatari800/include/win"
else:
    extra_compile_args = ["-g"]
    #extra_compile_args = ["-O3"]
    extra_link_args = []
    libatari800_config_include = "libatari800/include/linux"

extensions = [
    Extension("omni8bit.atari800.libatari800",
        sources = [
            "libatari800/atari800_bridge.c",
            "libatari800/libatari800.c",
            "libatari800/tinycthread.c",
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
            "libatari800/atari800/src/roms/altirra_5200_os.c",
            "libatari800/atari800/src/roms/altirraos_800.c",
            "libatari800/atari800/src/roms/altirraos_xl.c",
            "libatari800/atari800/src/roms/altirra_basic.c",
            "libdebugger/libdebugger.c",
        ],
        extra_compile_args = extra_compile_args,
        extra_link_args = extra_link_args,
        include_dirs = [libatari800_config_include, "libatari800/atari800/src", "libatari800/atari800/src/libatari800", "libdebugger", np.get_include()],
        undef_macros = [ "NDEBUG" ],
    ),
    Extension("omni8bit.generic6502.lib6502",
        sources = [
            "lib6502/lib6502.c",
            "lib6502/6502-emu_wrapper.c",
            "lib6502/6502-emu/6502.c",
            "libdebugger/libdebugger.c",
        ],
        extra_compile_args = extra_compile_args,
        extra_link_args = extra_link_args,
        include_dirs = ["lib6502", "lib6502/6502-emu", "libdebugger", np.get_include()],
        undef_macros = [ "NDEBUG" ],
    ),
    Extension("omni8bit.udis_fast.disasm_info",
        sources = [
            "libudis/disasm_info.c",
        ],
        extra_compile_args = extra_compile_args,
        include_dirs = [np.get_include()],
        ),
    Extension("omni8bit.udis_fast.disasm_speedups_monolithic",
        sources = [
            "libudis/disasm_speedups_monolithic.c",
            "libudis/hardcoded_parse_monolithic.c",
        ],
        extra_compile_args = extra_compile_args,
        include_dirs = [np.get_include()],
        ),
]

cmdclass = dict()

# Cython is only used when creating a source distribution. Users don't need
# to install Cython unless they are modifying the .pyx files themselves.
if "sdist" in sys.argv:
    import subprocess
    if not os.path.exists("omni8bit/udis_fast/cputables.py"):
        subprocess.run(['python', 'libudis/cpugen.py'])
    if not os.path.exists("libudis/disasm_speedups_monolithic.pyx"):
        subprocess.run(['python', 'libudis/disasm_gen.py'])
    try:
        from Cython.Build import cythonize
        from distutils.command.sdist import sdist as _sdist

        class sdist(_sdist):
            def run(self):
                cythonize(["libatari800/libatari800.pyx"], gdb_debug=True)
                cythonize(["lib6502/lib6502.pyx"], gdb_debug=True)
                cythonize(["libudis/disasm_info.pyx"], gdb_debug=True)
                cythonize(["libudis/disasm_speedups_monolithic.pyx"], gdb_debug=True)
                _sdist.run(self)
        cmdclass["sdist"] = sdist
    except ImportError:
        # assume the user doesn't have Cython and hope that the C file
        # is included in the source distribution.
        pass

exec(compile(open('omni8bit/_metadata.py').read(), 'omni8bit/_metadata.py', 'exec'))

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
    'construct<2.9',  # Construct 2.9 changed the String class
    'ply',
    ],
)
