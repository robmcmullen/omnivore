# Simple tasks application

# Standard library imports.
from pkg_resources import Environment, working_set
import logging

# Enthought library imports.
from traits.etsconfig.api import ETSConfig
from envisage.api import PluginManager, EggPluginManager
from envisage.composite_plugin_manager import CompositePluginManager
from envisage.core_plugin import CorePlugin
from envisage.ui.tasks.tasks_plugin import TasksPlugin
 
# Local imports.
from peppy2.framework.plugin import FrameworkPlugin
from peppy2.file_type.plugin import FileTypePlugin
from peppy2.framework.application import FrameworkApplication


# A list of the directories that contain the application's eggs (any directory
# not specified as an absolute path is treated as being relative to the current
# working directory).
EGG_PATH = ['eggs']


def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    plugins = [ CorePlugin(), TasksPlugin(), FrameworkPlugin(), FileTypePlugin() ]
    
    import peppy2.file_type.recognizers
    plugins.extend(peppy2.file_type.recognizers.plugins)
    
    # Find all additional eggs and add them to the working set
    environment = Environment(EGG_PATH)
    distributions, errors = working_set.find_plugins(environment)
    if len(errors) > 0:
        raise SystemError('cannot add eggs %s' % errors)
    logger.debug('added eggs %s' % distributions)
    map(working_set.add, distributions)

    # The plugin manager specifies which eggs to include and ignores all others
    egg = EggPluginManager(
        include = [
            'peppy2.tasks',
        ]
    )
    default = PluginManager(
        plugins = plugins,
    )
    plugin_manager = CompositePluginManager(
        plugin_managers=[default, egg]
    )

    app = FrameworkApplication(plugin_manager=plugin_manager)
    
    app.run()

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
