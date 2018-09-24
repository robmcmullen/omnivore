import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

exec(open('atrcopy/_metadata.py').read())

with open("README.rst", "r") as fp:
    long_description = fp.read()

if sys.platform.startswith("win"):
    scripts = ["scripts/atrcopy.bat"]
else:
    scripts = ["scripts/atrcopy"]

setup(name="atrcopy",
        version=__version__,
        author=__author__,
        author_email=__author_email__,
        url=__url__,
        packages=["atrcopy"],
        include_package_data=True,
        scripts=scripts,
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
