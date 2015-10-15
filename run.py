# Simple tasks application

# Standard library imports.
import logging
 
# Local imports.
from omnimon.framework.application import run


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

    run(egg_path=EGG_PATH)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
