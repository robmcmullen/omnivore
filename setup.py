import sys

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
            # "sawx.loaders": [
            #     'atrip = atrip.omnivore_loader',
            # ],

            "atrip.collections": [
                'zip = atrip.collections.zip',
            ],

            "atrip.containers": [
                'zlib = atrip.containers.zlib',
                'gzip = atrip.containers.gzip',
                'bzip = atrip.containers.bzip',
                'lzma = atrip.containers.lzma',
                'dcm = atrip.containers.dcm',
            ],

            "atrip.media_types": [
                'atari_disks = atrip.media_types.atari_disks',
                'atari_carts = atrip.media_types.atari_carts',
                'apple_disks = atrip.media_types.apple_disks',
            ],

            "atrip.filesystems": [
                'atari_dos = atrip.filesystems.atari_dos2',
                'kboot = atrip.filesystems.kboot',
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
        description="Utility to manage file systems on Atari 8-bit (DOS 2) and Apple ][ (DOS 3.3) disk images.",
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
        ],
        tests_require = [
            'pytest>3.0',
            'coverage',
            'pytest.cov',
        ],
    )
