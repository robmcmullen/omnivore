# All built-in recognizer plugins should be listed in this file so that the
# application can import this single file and determine the default plugins.
# In addition, a list of plugins is expected so that the framework can import
# all built-in plugins at once.
#
# A cog script is included to automatically generate the expected code. Test with::
#
#    cog.py __init__.py
#
# which prints to standard output. To place the generated code in the file, use::
#
#    cog.py -r __init__.py
#
# Note that the cog script works when called from the top directory (.i.e.  at
# the same level as the omnivore directory) or this directory.

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
#top = os.path.abspath(os.path.join(path, "../../..")) # so absolute imports of omnivore will work
#sys.path.append(top)
#cog.msg("top dir     : %s" % top)
#import glob
#cog.outl("plugins = []")
#for filename in glob.iglob(os.path.join(path, "*.py")):
#    if filename.endswith("__init__.py"):
#        continue
#    cog.msg("filename: %s" % filename)
#    modname = filename.split(".py")[0].split("/")[-1]
#    module = imp.load_source(modname, filename)
#    cog.msg("module: %s" % module.__name__)
#    members = inspect.getmembers(module, inspect.isclass)
#    names = []
#    for name, cls in members:
#        cog.msg("member: %s, cls %s, module %s" % (name, cls, cls.__module__))
#        if issubclass(cls, Plugin) and cls.__module__ == module.__name__:
#            names.append(name)
#    if names:
#       cog.outl("from %s import %s" % (modname, ", ".join(names)))
#       for name in names:
#           cog.outl("plugins.append(%s())" % name)
# ]]]*/
plugins = []
from exception_handler import ExceptionHandlerPlugin
plugins.append(ExceptionHandlerPlugin())
from file_progress import FileProgressPlugin
plugins.append(FileProgressPlugin())
from open_recent import OpenRecentPlugin
plugins.append(OpenRecentPlugin())
#[[[end]]]
