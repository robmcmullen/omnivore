"""peppy - (ap)Proximated (X)Emacs Powered by Python.

A full-featured editor for text files and more, Peppy provides an XEmacs-like
multi-window, multi-tabbed interface using the Enthought Tasks framework (only
wxPython is supported as a GUI backend).  It is built around the emacs concept
of major modes -- different views are presented to the user depending on the
type of data being edited.

Plugins
=======

Peppy is extended by plugins.  Plugins are based on the `Enthought Framework`__
and are discovered using setuptools plugins.

__ http://docs.enthought.com/envisage/envisage_core_documentation/index.html
"""

# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "https://github.com/robmcmullen/peppy2"
__download_url__ = "https://github.com/robmcmullen/peppy2/releases"
__bug_report_url__ = "https://github.com/robmcmullen/peppy2/issues"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, python, plugins"
__license__ = "GPL"

# The real version number is maintained in a file that's under version control
# so I don't have to keep updating and checking in the file
try:
    import _peppy_version
    __version__ = _peppy_version.version
    __codename__ = _peppy_version.codename
    __revision__ = _peppy_version.revision
except ImportError:
    __version__ = "git-dev"
    __codename__ = "git-codename"
    __revision__ = "HEAD"
