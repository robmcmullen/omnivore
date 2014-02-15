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


def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)

    plugins = [ CorePlugin(), TasksPlugin(), FrameworkPlugin(), FileTypePlugin() ]
    
    import peppy2.file_type.recognizers
    plugins.extend(peppy2.file_type.recognizers.plugins)
    
    app = FrameworkApplication(plugins=plugins)
    
    app.run()

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
