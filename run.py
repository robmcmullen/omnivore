#!/usr/bin/env python

# Standard library imports.
import logging

# A list of the directories that contain the application's eggs (any directory
# not specified as an absolute path is treated as being relative to the current
# working directory).
EGG_PATH = ['eggs']


def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)
    for toolkit in ['pyface', 'envisage', 'traits', 'traitsui', 'apptools']:
        _ = logging.getLogger(toolkit)
        _.setLevel(logging.WARNING)
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

    from omnivore.framework.application import run
    run(egg_path=EGG_PATH)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    
    # set up early py2exe logging redirection, saving any messages until the log
    # file directory can be determined after the application is initialized.
    frozen = getattr(sys, 'frozen', False)
    if frozen in ('dll', 'windows_exe', 'console_exe'):
        class Blackhole(object):
            softspace = 0
            saved_text = []
            def write(self, text):
                self.saved_text.append(text)
            def flush(self):
                pass
        sys.stdout = Blackhole()
        sys.stderr = sys.stdout
    
    main(sys.argv)
