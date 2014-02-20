# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "https://github.com/robmcmullen/peppy2"
__download_url__ = "https://github.com/robmcmullen/peppy2/releases"
__bug_report_url__ = "https://github.com/robmcmullen/peppy2/issues"
__keywords__ = "text editor, python, plugins"
__license__ = "GPL"
__requires__ = [
    'traits',
    'pyface',
    'traitsui',
    'apptools',
    'envisage',
]

# The real version number is maintained in a file that's under version control
# so I don't have to keep updating and checking in the file
try:
    import _peppy_version
    __version__ = _peppy_version.version
    __codename__ = _peppy_version.codename
    __revision__ = _peppy_version.revision
except ImportError:
    __version__ = "0.1.dev"
    __codename__ = "git-codename"
    __revision__ = "HEAD"
