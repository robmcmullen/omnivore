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
    if "-d" in argv:
        i = argv.index("-d")
        argv.pop(i)  # discard -d
        next = argv.pop(i)  # discard next
        if next == "all":
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
        else:
            loggers = next.split(",")
            for name in loggers:
                log = logging.getLogger(name)
                log.setLevel(logging.DEBUG)

    else:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
    for toolkit in ['pyface', 'envisage', 'traits', 'traitsui', 'apptools']:
        _ = logging.getLogger(toolkit)
        _.setLevel(logging.WARNING)

    run(egg_path=EGG_PATH)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    main(sys.argv)
