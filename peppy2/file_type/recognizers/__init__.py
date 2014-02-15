# All built-in recognizer plugins should be listed in this file so that the
# application can import this single file and determine the default plugins.
# In addition, a list of plugins is expected so that the framework can import
# all built-in plugins at once.
#
# A cog script is included to automatically generate the expected code. Test with::
#
#    cog __init__.py
#
# which prints to standard output. To place the generated code in the file, use::
#
#    cog -r __init__.py
#
# Note that the cog script works when called from the top directory (.i.e.  at
# the same level as the peppy2 directory) or this directory.

# [[[cog
#import os
#import sys
#import inspect
#import imp
#
#from envisage.api import Plugin
#
#cwd = os.getcwd()
#cog.msg("working dir : %s" % cwd)
#path = os.path.dirname(os.path.join(cwd, cog.inFile))
#cog.msg("scanning dir: %s" % path)
#top = os.path.abspath(os.path.join(path, "../../..")) # so absolute imports of peppy2 will work
#sys.path.append(top)
#cog.msg("top dir     : %s" % top)
#import glob
#cog.outl("plugins = []")
#for filename in glob.iglob(os.path.join(path, "*.py")):
#    if filename.endswith("__init__.py"):
#        continue
#    modname = filename.rstrip(".py").split("/")[-1]
#    module = imp.load_source(modname, filename)
#    members = inspect.getmembers(module, inspect.isclass)
#    for name, pluginclass in members:
#        if issubclass(pluginclass, Plugin):
#            # make sure class is from this module and not an imported dependency
#            if pluginclass.__module__.startswith(modname):
#                cog.outl("from %s import %s" % (modname, name))
#                cog.outl("plugins.append(%s())" % name)
# ]]]*/
plugins = []
from image import ImageRecognizerPlugin
plugins.append(ImageRecognizerPlugin())
# [[[end]]]

