# Simple tasks application

# Standard library imports.
import logging

# Enthought library imports.
from traits.etsconfig.api import ETSConfig
from envisage.core_plugin import CorePlugin
from envisage.ui.tasks.tasks_plugin import TasksPlugin
 
# Local imports.
from peppy2.framework.plugin import FrameworkPlugin
from peppy2.file_type.plugin import FileTypePlugin
from peppy2.framework.application import FrameworkApplication


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
    
    import peppy2.file_type.recognizers
    add_plugins(peppy2.file_type.recognizers, plugins)
    
    app = FrameworkApplication(plugins=plugins)
    
    app.run()

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
