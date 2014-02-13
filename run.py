# Simple tasks application

# Standard library imports.
import logging

# Plugin imports.
from envisage.core_plugin import CorePlugin
from envisage.ui.tasks.tasks_plugin import TasksPlugin
from framework.plugin import FrameworkPlugin
from file_type.plugin import FileTypePlugin
 
# Local imports.
from framework.application import FrameworkApplication


def add_plugins(module, plugins):
    from envisage.api import Plugin
    import inspect
    
    members = inspect.getmembers(module, inspect.isclass)
    print members
    for name, pluginclass in members:
        if issubclass(pluginclass, Plugin):
            plugin = pluginclass()
            print "Adding %s plugin %s: %s" % (str(module), name, plugin)
            plugins.append(plugin)

def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)

    plugins = [ CorePlugin(), TasksPlugin(), FrameworkPlugin(), FileTypePlugin() ]
    
    import file_type.recognizers
    add_plugins(file_type.recognizers, plugins)
    
    app = FrameworkApplication(plugins=plugins)
    
    app.run()

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
