# Import the toolkit specific version.
import os
import sys

_toolkit_backend_name = None


def _init_toolkit():
    from pyface.toolkit import _toolkit_backend
    backend = _toolkit_backend.strip(".").split(".")[-1]

    global _toolkit_backend_name
    _toolkit_backend_name = "_" + backend


# Do this once then disappear.
_init_toolkit()
del _init_toolkit


def toolkit_object(mname, oname):
    """Add the toolkit specific object with the given name to the namespace given by mname.
    
    This paradigm is different than the Enthough/Pyface library that puts
    the toolkit-specific code in ui/[wx|qt4]/ subdirectories.  This function
    imports toolkit-specific code from files adjacent to the generic code.
    For example, if the generic module is named test_widget.py, the toolkit-
    specific code should reside in test_widget_wx.py and test_widget_qt4.py in
    the same directory.
    
    Typical use of this function would be to use the following two-line block
    of code in the generic module (e.g.  test_widget.py):
    
        from framework_toolkit import toolkit_object
        toolkit_object(__name__, 'TestWidget')
    
    :param str mname: the full module name of the generic module, typically __name__
    :param str oname: The object name to import as the toolkit-specific version of the generic module
    """

    be_mname = mname + _toolkit_backend_name

    class Unimplemented(object):
        """ This is returned if an object isn't implemented by the selected
        toolkit.  It raises an exception if it is ever instantiated.
        """

        def __init__(self, *args, **kwargs):
            raise NotImplementedError("the %s pyface backend doesn't implement %s" % (ETSConfig.toolkit, oname))

    be_obj = Unimplemented

    try:
        __import__(be_mname)

        try:
            be_obj = getattr(sys.modules[be_mname], oname)
            setattr(sys.modules[mname], oname, be_obj)
        except AttributeError:
            pass
    except ImportError, e:

        # Ignore *ANY* errors unless a debug ENV variable is set.
        if 'ETS_DEBUG' in os.environ:
            raise
