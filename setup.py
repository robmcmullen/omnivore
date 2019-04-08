import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

exec(compile(open('atree/_version.py').read(), 'atree/_version.py', 'exec'))
exec(compile(open('atree/_metadata.py').read(), 'atree/_metadata.py', 'exec'))

with open("README.rst", "r") as fp:
    long_description = fp.read()

if sys.platform.startswith("win"):
    scripts = ["scripts/atree.bat"]
else:
    scripts = ["scripts/atree"]

setup(name="atree",
        version=__version__,
        author=__author__,
        author_email=__author_email__,
        url=__url__,
        packages=["atree"],
        include_package_data=True,
        scripts=scripts,
        entry_points={
            # "sawx.loaders": [
            #     'atree = atree.omnivore_loader',
            # ],

            "atree.collections": [
                'zip = atree.collections.zip',
            ],

            "atree.containers": [
                'zlib = atree.containers.zlib',
                'gzip = atree.containers.gzip',
                'bzip = atree.containers.bzip',
                'lzma = atree.containers.lzma',
                'dcm = atree.containers.dcm',
            ],

            "atree.media_types": [
                'atari_disks = atree.media_types.atari_disks',
                'atari_carts = atree.media_types.atari_carts',
                'apple_disks = atree.media_types.apple_disks',
            ],

            "atree.filesystems": [
                'atari_dos = atree.filesystems.atari_dos2',
                'kboot = atree.filesystems.kboot',
            ],

            "atree.file_types": [
                'atari_xex = atree.file_types.atari_xex',
            ],

            "atree.signatures": [
                'atari2600_cart = atree.signatures.atari2600_cart',
                'atari2600_starpath = atree.signatures.atari2600_starpath',
                'atari5200_cart = atree.signatures.atari5200_cart',
                'vectrex = atree.signatures.vectrex',
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
