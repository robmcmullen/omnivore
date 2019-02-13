import sys
import argparse

import logging
log = logging.getLogger(__name__)

import wx

from traits.api import push_exception_handler
push_exception_handler(reraise_exceptions=True)

def setup_frozen_logging():
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


def run(app_cls, image_paths=[], template_paths=[], debug_log=False):
    from . import filesystem
    from .utils.jobs import get_global_job_manager

    filesystem.image_paths.extend(image_paths)

    from .templates import template_subdirs
    template_subdirs.extend(template_paths)

    # Create a debugging log
    if debug_log:
        filename = app.get_log_file_name("debug")
        handler = logging.FileHandler(filename)
        logger = logging.getLogger('')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    # Turn off omnivore log debug messages by default
    log = logging.getLogger("omnivore_framework")
    log.setLevel(logging.INFO)

    app = app_cls()

    app.process_command_line_args(sys.argv[1:])

    app.MainLoop()

    job_manager = get_global_job_manager()
    if job_manager is not None:
        job_manager.shutdown()
