import os
import sys
import subprocess
from setuptools import setup, find_packages, Extension
import glob
from distutils.command.clean import clean
try:
    import numpy as np
except ImportError:
    sys.exit('Please install numpy first, e.g. "pip install numpy"')

if sys.version_info < (3, 6):
    sys.exit('Omnivore requires Python 3.6 or higher')

try:
    from Cython.Build import cythonize
except ImportError:
    def cythonize(args):
        missing = []
        for ext in args:
            for src in ext.sources:
                if src.endswith(".pyx"):
                    gen = src[:-4] + ".c"
                    if not os.path.exists(gen):
                        missing.append(gen)
        if missing:
            print("Cython is required because this version was not shipped with the cythonized C files:")
            print("\n".join(missing))
            sys.exit(1)
        return args


if sys.platform.startswith("win"):
    extra_compile_args = ["-DMSVC", "-D_CRT_SECURE_NO_WARNINGS", "/Zi"]
    extra_link_args=['/DEBUG']
    libatari800_config_include = "libatari800/include/win"
else:
    extra_compile_args = ["-g"]
    #extra_compile_args = ["-Og"]
    #extra_compile_args = ["-O3"]
    extra_link_args = []
    libatari800_config_include = "libatari800/include/linux"

# extra_compile_args.append("-DDEBUG_THREAD_STATUS")
# extra_compile_args.append("-DDEBUG_REGISTER_CALLBACK")
# extra_compile_args.append("-DDEBUG_BREAKPOINT")
# extra_compile_args.append("-DDEBUG_POSTFIX_STACK")


class clean_py(clean):
    def run(self):
        clean.run(self)
        files = [
            "omnivore/*/*.so",
            "omnivore/*/*.pyd",
            "omnivore/*/*/*.so",
            "omnivore/*/*/*.pyd",
            "omnivore/arch/antic_speedups.c",
            "omnivore/disassembler/cputables.py",
            "lib6502/lib6502.c",
            "libatari800/libatari800.c",
            "libmac65/libmac65.c",
            "libudis/declarations.pyx",
            "libudis/declarations.c",
            "libudis/libudis.c",
            "libudis/parse_udis_cpu.c",
            "libudis/stringify_udis_cpu.c",
            "libudis/stringify_udis_cpu.h",
        ]
        for pathspec in files:
            for path in glob.glob(pathspec):
                print("cleaning" + str(path))
                try:
                    os.unlink(path)
                except OSError:
                    pass

if "clean" in sys.argv:
    # prevent extensions from being 
    ext_modules = []
else:
    cputables_path = "omnivore/disassembler/cputables.py"
    parse_gen_path = "libudis/parse_udis_cpu.c"
    if not os.path.exists(cputables_path):
        subprocess.run([sys.executable, 'libudis/cpugen.py'])
    out = {}
    exec(compile(open(cputables_path).read(), cputables_path, 'exec'), out)
    processors = out['processors']
    if '6502' not in processors:
        for path in [cputables_path, parse_gen_path]:
            try:
                os.unlink(path)
            except IOError:
                pass
        sys.exit("Disassemblers not generated; try 'git submodule init; git submodule update' and rerun.")

    if not os.path.exists(parse_gen_path):
        subprocess.run([sys.executable, 'libudis/parse_gen.py'])

    extensions = [
        Extension("omnivore.arch.antic_speedups",
                  sources=["omnivore/arch/antic_speedups.pyx"],
                  extra_compile_args = extra_compile_args,
                  extra_link_args = extra_link_args,
                  include_dirs = [np.get_include()],
                  ),
        Extension("omnivore.arch.pixel_speedups",
                  sources=["omnivore/arch/pixel_speedups.pyx"],
                  extra_compile_args = extra_compile_args,
                  extra_link_args = extra_link_args,
                  include_dirs = [np.get_include()],
                  ),
        Extension("omnivore.emulator.atari8bit.libatari800",
            sources = [
                "libatari800/atari800_bridge.c",
                "libatari800/atari800_antic.c",
                "libatari800/atari800_cpu.c",
                "libatari800/libatari800.pyx",
                "libatari800/tinycthread.c",
                "libatari800/atari800/src/libatari800/main.c",
                "libatari800/atari800/src/libatari800/input.c",
                "libatari800/atari800/src/libatari800/video.c",
                "libatari800/atari800/src/libatari800/init.c",
                "libatari800/atari800/src/libatari800/sound.c",
                "libatari800/atari800/src/libatari800/statesav.c",
                "libatari800/atari800/src/afile.c",
                # "libatari800/atari800/src/antic.c",
                "libatari800/atari800/src/atari.c",
                "libatari800/atari800/src/binload.c",
                "libatari800/atari800/src/cartridge.c",
                "libatari800/atari800/src/cassette.c",
                "libatari800/atari800/src/compfile.c",
                "libatari800/atari800/src/cfg.c",
                # "libatari800/atari800/src/cpu.c",
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
                "libudis/history.c",
            ],
            depends = [
                "libatari800/atari800_bridge.h",
                "libatari800/tinycthread.h",
                "libatari800/include/linux/config.h",
                "libatari800/include/win/config.h",
                "libatari800/include/win/dirent.h",
                "libatari800/atari800/src/libatari800/libatari800.h",
                "libatari800/atari800/src/libatari800/main.h",
                "libatari800/atari800/src/libatari800/input.h",
                "libatari800/atari800/src/libatari800/video.h",
                "libatari800/atari800/src/libatari800/init.h",
                "libatari800/atari800/src/libatari800/sound.h",
                "libatari800/atari800/src/libatari800/statesav.h",
                "libatari800/atari800/src/afile.h",
                "libatari800/atari800/src/antic.h",
                "libatari800/atari800/src/atari.h",
                "libatari800/atari800/src/binload.h",
                "libatari800/atari800/src/cartridge.h",
                "libatari800/atari800/src/cassette.h",
                "libatari800/atari800/src/compfile.h",
                "libatari800/atari800/src/cfg.h",
                "libatari800/atari800/src/cpu.h",
                "libatari800/atari800/src/crc32.h",
                "libatari800/atari800/src/devices.h",
                "libatari800/atari800/src/esc.h",
                "libatari800/atari800/src/gtia.h",
                "libatari800/atari800/src/img_tape.h",
                "libatari800/atari800/src/log.h",
                "libatari800/atari800/src/memory.h",
                "libatari800/atari800/src/monitor.h",
                "libatari800/atari800/src/pbi.h",
                "libatari800/atari800/src/pia.h",
                "libatari800/atari800/src/pokey.h",
                "libatari800/atari800/src/rtime.h",
                "libatari800/atari800/src/sio.h",
                "libatari800/atari800/src/sysrom.h",
                "libatari800/atari800/src/util.h",
                "libatari800/atari800/src/input.h",
                "libatari800/atari800/src/statesav.h",
                "libatari800/atari800/src/ui.h",
                "libatari800/atari800/src/artifact.h",
                "libatari800/atari800/src/colours.h",
                "libatari800/atari800/src/colours_ntsc.h",
                "libatari800/atari800/src/colours_pal.h",
                "libatari800/atari800/src/colours_external.h",
                "libatari800/atari800/src/screen.h",
                "libatari800/atari800/src/cycle_map.h",
                "libatari800/atari800/src/pbi_mio.h",
                "libatari800/atari800/src/pbi_bb.h",
                "libatari800/atari800/src/pbi_scsi.h",
                "libatari800/atari800/src/pokeysnd.h",
                "libatari800/atari800/src/mzpokeysnd.h",
                "libatari800/atari800/src/remez.h",
                "libatari800/atari800/src/sndsave.h",
                "libatari800/atari800/src/sound.h",
                "libatari800/atari800/src/pbi_xld.h",
                "libatari800/atari800/src/voicebox.h",
                "libatari800/atari800/src/votrax.h",
                "libatari800/atari800/src/votraxsnd.h",
                "libatari800/atari800/src/roms/altirra_5200_os.h",
                "libatari800/atari800/src/roms/altirraos_800.h",
                "libatari800/atari800/src/roms/altirraos_xl.h",
                "libatari800/atari800/src/roms/altirra_basic.h",
                "libdebugger/libdebugger.h",
                "libudis/libudis.h",
                "libudis/libudis_flags.h",
            ],
            extra_compile_args = extra_compile_args,
            extra_link_args = extra_link_args,
            include_dirs = [libatari800_config_include, "libatari800/atari800/src", "libatari800/atari800/src/libatari800", "libdebugger", "libudis", np.get_include()],
            undef_macros = [ "NDEBUG" ],
        ),
        Extension("omnivore.emulator.generic6502.lib6502",
            sources = [
                "lib6502/lib6502.pyx",
                "lib6502/6502-emu_wrapper.c",
                "lib6502/6502-emu/6502.c",
                "libdebugger/libdebugger.c",
                "libudis/history.c",
            ],
            depends = [
                "lib6502/6502-emu_wrapper.h",
                "lib6502/6502-emu/6502.h",
                "libdebugger/libdebugger.h",
                "libudis/libudis.h",
                "libudis/libudis_flags.h",
            ],
            extra_compile_args = extra_compile_args,
            extra_link_args = extra_link_args,
            include_dirs = ["lib6502", "lib6502/6502-emu", "libdebugger", "libudis", np.get_include()],
            undef_macros = [ "NDEBUG" ],
        ),
        Extension("omnivore.disassembler.libudis",
            sources = [
                "libudis/libudis.pyx",
                "libudis/parse_udis_cpu.c",
                "libudis/parse_custom.c",
                "libudis/stringify_udis_cpu.c",
                "libudis/stringify_custom.c",
                "libudis/history.c",
            ],
            depends = [
                "libudis/libudis.h",
                "libudis/libudis_flags.h",
            ],
            extra_compile_args = extra_compile_args,
            include_dirs = ["libdebugger", "libudis", np.get_include()],
            ),
        Extension("atrip.assemblers.libmac65",
            sources = [
                "libmac65/libmac65.pyx",
                "libmac65/cython_interface.c",
                "libmac65/atasm/src/asm.c",
                "libmac65/atasm/src/symbol.c",
                "libmac65/atasm/src/parser.c",
                "libmac65/atasm/src/setparse.c",
                "libmac65/atasm/src/inc_path.c",
                "libmac65/atasm/src/crc32.c",
                "libmac65/atasm/src/atasm_err.c",
                ],
            depends = [
                "libmac65/atasm/src/atasm_err.h",
                "libmac65/atasm/src/compat.h",
                "libmac65/atasm/src/directive.h",
                "libmac65/atasm/src/inc_path.h",
                "libmac65/atasm/src/ops.h",
                "libmac65/atasm/src/symbol.h",
                ],
          extra_compile_args = extra_compile_args,
          include_dirs = ["libmac65/atasm/src"],
          )
    ]
    ext_modules = cythonize(extensions)

exec(compile(open('omnivore/_version.py').read(), 'omnivore/_version.py', 'exec'))
exec(compile(open('omnivore/_metadata.py').read(), 'omnivore/_metadata.py', 'exec'))

setup(
    name = "omnivore",
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
    ext_modules = ext_modules,
    packages = find_packages(exclude=["libudis"]),
    include_package_data=True,
    scripts = [
        "scripts/atrip",
        "scripts/omnivore",
    ],
    entry_points={
        "atrip.archivers": [
            'zip = atrip.archivers.zip',
            'tar = atrip.archivers.tar',
        ],

        "atrip.assemblers": [
            'mac65 = atrip.assemblers.mac65',
        ],

        "atrip.compressors": [
            'zlib = atrip.compressors.zlib',
            'gzip = atrip.compressors.gzip',
            'bzip = atrip.compressors.bzip',
            'lzma = atrip.compressors.lzma',
            'Z = atrip.compressors.unix_compress',
            'lz4 = atrip.compressors.lz4',
            'dcm = atrip.compressors.dcm',
        ],

        "atrip.stringifiers": [
            'hexify = atrip.stringifiers.hexify',
            'c_bytes = atrip.stringifiers.c_bytes',
            'basic_data = atrip.stringifiers.basic_data',
        ],

        "atrip.media_types": [
            'atari_disks = atrip.media_types.atari_disks',
            'atari_carts = atrip.media_types.atari_carts',
            'atari_tapes = atrip.media_types.atari_tapes',
            'apple_disks = atrip.media_types.apple_disks',
        ],

        "atrip.filesystems": [
            'atari_dos = atrip.filesystems.atari_dos2',
            'atari_cas = atrip.filesystems.atari_cas',
            'atari_jumpman = atrip.filesystems.atari_jumpman',
            'kboot = atrip.filesystems.kboot',
            'apple_dos33 = atrip.filesystems.apple_dos33',
        ],

        "atrip.file_types": [
            'atari_xex = atrip.file_types.atari_xex',
        ],

        "atrip.signatures": [
            'atari2600_cart = atrip.signatures.atari2600_cart',
            'atari2600_starpath = atrip.signatures.atari2600_starpath',
            'atari5200_cart = atrip.signatures.atari5200_cart',
            'vectrex = atrip.signatures.vectrex',
        ],

        "omnivore.viewers": [
            'bitmap = omnivore.viewers.bitmap',
            'pixelmap = omnivore.viewers.pixelmap',
            'char = omnivore.viewers.char',
            'hex = omnivore.viewers.hex',
            'info = omnivore.viewers.info',
            'map = omnivore.viewers.map',
            'jumpman = omnivore.viewers.jumpman',
            'emulator = omnivore.viewers.emulator',
            'apple2 = omnivore.viewers.apple2',
            'memory = omnivore.viewers.memory',
            'skeleton = omnivore.viewers.skeleton',
            'disasm = omnivore.viewers.disasm',
            'history = omnivore.viewers.history',
        ],

        "sawx.documents": [
            '00byte = omnivore.document',
            '99text = sawx.documents.text',
        ],

        "sawx.editors": [
            '00byte = omnivore.editors.byte_editor',
            'html = sawx.editors.html_viewer',
            'text = sawx.editors.text_editor',
        ],

        "sawx.loaders": [
            '00atrip = atrip.omnivore_loader',
            '99fleep = sawx.loaders.fleep',
            '98text = sawx.loaders.text',
        ],

        "sawx.remember": [
            'fonts = omnivore.arch.fonts',
            'app = sawx.application',
        ],
    },
    platforms = ["Windows", "Linux", "Mac OS-X", "Unix"],
    zip_safe = False,
    install_requires = [
    'pathlib2',  # pip install processes from the top down!
    'numpy',

    'python-slugify',
    'ply',
    'lz4',
    'construct<2.9',  # Construct 2.9 changed the String class
    'pytz',
    'pyparsing',
    'configobj',
    'bson<1.0.0',
    'jsonpickle',
    # 'pyopengl-accelerate',  # not required, and a pain on some platform/os combos
    'pyopengl',
    'fleep',  # not actually required
    'appdirs',
    'wxpython',
    'pillow',
    'six',

    'numpy',
    'pathlib2',  # python setup.py develop processes from the bottom up!
    ],
    cmdclass = {"clean": clean_py},
)
