# Simple tasks application

# Standard library imports.
import logging

# Plugin imports.
from envisage.core_plugin import CorePlugin
from envisage.ui.tasks.tasks_plugin import TasksPlugin
from framework.plugin import FrameworkPlugin

# Local imports.
from framework.application import FrameworkApplication


def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)

    plugins = [ CorePlugin(), TasksPlugin(), FrameworkPlugin() ]
    app = FrameworkApplication(plugins=plugins)
    
    app.run()

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
