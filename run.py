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

def create_global_functions():
    def what_called_me():
        import traceback
        stack = traceback.extract_stack()
        count = len(stack) - 2
        for i, item in enumerate(stack[:-1]):
            print("#%d %s in %s at %s:%d" % (count - i, item[3], item[2], item[0], item[1]))
    import __builtin__
    __builtin__.what_called_me = what_called_me

create_global_functions()

def main(argv):
    """ Run the application.
    """
    logging.basicConfig(level=logging.WARNING)
    for toolkit in ['pyface', 'envisage', 'traits', 'traitsui', 'apptools']:
        _ = logging.getLogger(toolkit)
        _.setLevel(logging.WARNING)

    # check for logging early so we can get logging output during application init
    import omnivore.utils.wx.error_logger as error_logger
    if "-d" in argv:
        i = argv.index("-d")
        error_logger.enable_loggers(argv[i+1])
    else:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

    if "--trace" in argv:
        i = argv.index("--trace")
        argv.pop(i)
        sys.settrace(trace_calls)

    from omnivore8bit.plugin import OmnivoreEditorPlugin
    plugins = [OmnivoreEditorPlugin()]

    import omnivore8bit.file_type
    plugins.extend(omnivore8bit.file_type.plugins)
    
    import omnivore8bit.viewers
    plugins.extend(omnivore8bit.viewers.plugins)

    # Crypto is separated to make it easy to make it optional for those
    # framework users who don't want the extra dependencies
    import omnivore_extra.crypto.file_type
    plugins.extend(omnivore_extra.crypto.file_type.plugins)

    from omnivore.app_init import run
    from omnivore8bit.document import SegmentedDocument
    run(plugins=plugins, use_eggs=False, document_class=SegmentedDocument)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    from omnivore.app_init import setup_frozen_logging
    
    setup_frozen_logging()
    main(sys.argv)
