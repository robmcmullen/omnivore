#!/usr/bin/env python

# Standard library imports.
import sys
import logging


last_trace_was_system_call = False
trace_after_funcname = None

def trace_calls(frame, event, arg):
    global last_trace_was_system_call, trace_after_funcname

    # if event != 'call':
    #     return
    co = frame.f_code
    func_name = co.co_name
    # if func_name == 'write':
    #     # Ignore write() calls from print statements
    #     return
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
    # if "/python2.7" in caller_filename or "agw/aui" in func_filename or "agw/aui" in caller_filename or "/logging/" in func_filename or "/wx/core.py" in func_filename or "/traits/" in func_filename or "/traits/" in caller_filename or "/traitsui/" in func_filename or "/traitsui/" in caller_filename or "/sre_" in caller_filename or "/logging/" in caller_filename:
    if "/logging/" in caller_filename:
        return
    #     if not last_trace_was_system_call:
    #         print('  <system calls>')
    #         last_trace_was_system_call = True
    #     return
    last_trace_was_system_call = False
    print(f'{event}: %s:%s -> %s %s:%s' % (caller_filename, caller_line_no, func_name, func_filename, func_line_no))
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

    from sawx.startup import run
    from sawx.application import SawxApp
    from sawx.filesystem import get_image_path
    import omnivore
    import atrip

    image_paths = [get_image_path("icons", omnivore)]
    template_paths = [get_image_path("templates", omnivore), get_image_path("templates/fonts", omnivore), atrip.get_template_path()]

    from omnivore._version import __version__
    OmnivoreApp = SawxApp
    OmnivoreApp.app_name = "Omnivore"
    OmnivoreApp.app_version = __version__
    OmnivoreApp.app_icon = "icon://omnivore.ico"
    OmnivoreApp.app_description = "The 8-bit Reverse Engineering Toolbox"
    OmnivoreApp.app_website = "https://playermissile.com/omnivore"
    OmnivoreApp.about_dialog_credits = f"""Contributors:<ul>
<li>Kevin Savetz of <a href=\"http://ataripodcast.com\">ANTIC, the Atari 8-bit Podcast</a> for beta testing
<li>Wade Ripkowski of <a href=\"http://inverseatascii.info\">Inverse ATASCII, the Atari 8-bit Productivity Podcast</a> for beta testing
<li>Jeff Tranter for his work on <a href=\"https://github.com/robmcmullen/udis\">udis</a>, which became the basis for my Cython-based fast disassembler
<li>Charles Mangin for the Apple ][ and KIM-1 memory maps
<li>Steve Boswell for the <a href=\"https://github.com/ChoccyHobNob/EightBit-Atari-Fonts\">huge selection of Atari 8-bit fonts</a>
</ul>
"""
    OmnivoreApp.app_blank_page = f"""<html>
<h2>{OmnivoreApp.app_name} {OmnivoreApp.app_version}</h2>

<h3>{OmnivoreApp.app_description}</h3>

<p><img src="icon://omnivore256.png">"""

    run(OmnivoreApp, image_paths, template_paths)

    logging.shutdown()


if __name__ == '__main__':
    import sys
    from sawx.startup import setup_frozen_logging
    
    setup_frozen_logging()
    main(sys.argv)
