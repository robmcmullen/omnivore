#!/usr/bin/env python

# Standard library imports.
import sys
import logging


# A list of the directories that contain the application's eggs (any directory
# not specified as an absolute path is treated as being relative to the current
# working directory).
EGG_PATH = ['eggs']

last_trace_was_system_call = False
trace_after_funcname = None

def trace_calls(frame, event, arg):
    global last_trace_was_system_call, trace_after_funcname

    if event != 'call':
        return
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        # Ignore write() calls from print statements
        return
    if trace_after_funcname is not None:
        if func_name == trace_after_funcname:
            trace_after_funcname = None
        else:
            # skip anything until it hits the trace_after function
            return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename
    caller = frame.f_back
    caller_line_no = caller.f_lineno
    caller_filename = caller.f_code.co_filename
    if "/python2.7" in caller_filename or "agw/aui" in func_filename or "agw/aui" in caller_filename or "/logging/" in func_filename or "/wx/core.py" in func_filename or "/traits/" in func_filename or "/traits/" in caller_filename or "/traitsui/" in func_filename or "/traitsui/" in caller_filename or "/sre_" in caller_filename or "/logging/" in caller_filename:
        if not last_trace_was_system_call:
            print('  <system calls>')
            last_trace_was_system_call = True
        return
    last_trace_was_system_call = False
    print('%s:%s -> %s %s:%s' % (caller_filename, caller_line_no, func_name, func_filename, func_line_no))
    return

def create_global_functions():
    def what_called_me():
        import traceback
        stack = traceback.extract_stack()
        count = len(stack) - 2
        for i, item in enumerate(stack[:-1]):
            print(("#%d %s in %s at %s:%d" % (count - i, item[3], item[2], item[0], item[1])))
    import builtins
    builtins.what_called_me = what_called_me

create_global_functions()

# # Force wx toolkit to be imported before loading plugins
# from pyface.toolkit import toolkit_object
# toolkit_object("init:_app")

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

    if "--trace-after" in argv:
        global trace_after_funcname
        i = argv.index("--trace-after")
        argv.pop(i)
        funcname = argv.pop(i)
        trace_after_funcname = funcname
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
