import sys

if sys.version_info < (3, 6):
    sys.exit('Omnivore requires Python 3.6 or higher')

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

exec(compile(open('atrip/_version.py').read(), 'atrip/_version.py', 'exec'))
exec(compile(open('atrip/_metadata.py').read(), 'atrip/_metadata.py', 'exec'))

with open("README.rst", "r") as fp:
    long_description = fp.read()

if sys.platform.startswith("win"):
    scripts = ["scripts/atrip.bat"]
else:
    scripts = ["scripts/atrip"]

setup(name="atrip",
        version=__version__,
        author=__author__,
        author_email=__author_email__,
        url=__url__,
        packages=["atrip"],
        include_package_data=True,
        scripts=scripts,
        entry_points={
            "sawx.loaders": [
                '00atrip = atrip.omnivore_loader',
            ],

            "atrip.archivers": [
                'zip = atrip.archivers.zip',
                'tar = atrip.archivers.tar',
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
        },
        description="Utility to manage file systems on retro computer disk images",
        long_description=long_description,
        license="GPL",
        classifiers=[
            "Programming Language :: Python :: 3.6",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Topic :: Software Development :: Libraries",
            "Topic :: Utilities",
        ],
        python_requires = '>=3.6',
        install_requires = [
            'numpy',
            'jsonpickle',
            'lz4',
        ],
        tests_require = [
            'pytest>3.0',
            'coverage',
            'pytest.cov',
        ],
    )
