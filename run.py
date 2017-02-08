#!/usr/bin/env python

# Standard library imports.
import sys
import logging

# A list of the directories that contain the application's eggs (any directory
# not specified as an absolute path is treated as being relative to the current
# working directory).
EGG_PATH = ['eggs']

def trace_calls(frame, event, arg):
    if event != 'call':
        return
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        # Ignore write() calls from print statements
        return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename
    caller = frame.f_back
    caller_line_no = caller.f_lineno
    caller_filename = caller.f_code.co_filename
    print 'Call to %s on line %s of %s from line %s of %s' % \
        (func_name, func_line_no, func_filename,
         caller_line_no, caller_filename)
    return

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

    if "--trace" in argv:
        i = argv.index("--trace")
        argv.pop(i)
        sys.settrace(trace_calls)

    from omnivore.framework.application import run
    run(egg_path=EGG_PATH)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    from omnivore.framework.application import setup_frozen_logging
    
    setup_frozen_logging()
    main(sys.argv)
