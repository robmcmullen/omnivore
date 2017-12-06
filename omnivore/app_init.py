import sys
import argparse

try:
    # Force wx toolkit because pyface 5 uses entry points to determine
    # toolkits and I can't figure out how to get that to work in
    # executable bundlers. It has to be included before any calls to
    # any pyface modules so the monkey patch can intercept it before
    # an import of pyface.toolkit.
    from pyface.base_toolkit import Toolkit
    class MonkeyPatchPyface(object):
        toolkit_object = Toolkit('wx', 'pyface.ui.wx')
    sys.modules["pyface.toolkit"] = MonkeyPatchPyface()
except ImportError:
    # An import error means this is an older version of pyface and
    # does not need this hack.
    pass

import logging
log = logging.getLogger(__name__)

# Create the wx app here so we can capture the Mac specific stuff that
# traitsui.wx.toolkit's wx creation routines don't handle.  Also, monkey
# patching wx.GetApp() to add MacOpenFile (etc) doesn't seem to work, so we
# have to have these routines at app creation time.
import wx


class EnthoughtWxApp(wx.App):
    mac_menubar_app_name = "Omnivore"

    def OnInit(self):
        # Set application name before anything else
        self.SetAppName(self.mac_menubar_app_name)
        return True

    def MacOpenFiles(self, filenames):
        """OSX specific routine to handle files that are dropped on the icon
        
        """
        if hasattr(self, 'tasks_application'):
            # The tasks_application attribute is added to this wx.App instance
            # when the application has been initialized.  This is used as a
            # flag to indicate that the subsequent calls to MacOpenFile are
            # real drops of files onto the dock icon.  Prior to that, this
            # method gets called for all the command line arguments which would
            # give us two copies of each file specified on the command line.
            for filename in filenames:
                log.debug("MacOpenFile: loading %s" % filename)
                self.tasks_application.load_file(filename, None)
        else:
            log.debug("MacOpenFile: skipping %s because it's a command line argument" % str(filenames))

    throw_out_next_wheel_rotation = False

    def FilterEventMouseWheel(self, evt):
        if hasattr(evt, "GetWheelRotation"):
            print "FILTEREVENT!!!", evt.GetWheelRotation(), evt
            wheel = evt.GetWheelRotation()
            if wheel != 0:
                if self.throw_out_next_wheel_rotation:
                    self.throw_out_next_wheel_rotation = False
                    return 0
                self.throw_out_next_wheel_rotation = True
        if hasattr(evt, "GetKeyCode"):
            print "FILTEREVENT!!! char=%s, key=%s, modifiers=%s" % (evt.GetUnicodeKey(), evt.GetKeyCode(), bin(evt.GetModifiers()))
        return -1


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


def run(plugins=[], use_eggs=True, egg_path=[], image_path=[], template_path=[], startup_task="", application_name="Omnivore", debug_log=False, document_class=None):
    """Start the application
    
    :param plugins: list of user plugins
    :param use_eggs Boolean: search for setuptools plugins and plugins in local eggs?
    :param egg_path: list of user-specified paths to search for more plugins
    :param startup_task string: task factory identifier for task shown in initial window
    :param application_name string: change application name instead of default Omnivore
    """
    EnthoughtWxApp.mac_menubar_app_name = application_name
    _app = EnthoughtWxApp(redirect=False)
    if False:  # enable this to use FilterEvent
        _app.FilterEvent = _app.FilterEventMouseWheel

    # Enthought library imports.
    from envisage.api import PluginManager
    from envisage.core_plugin import CorePlugin

    # Local imports.
    from omnivore.framework.application import FrameworkApplication
    from omnivore.framework.plugin import OmnivoreTasksPlugin, OmnivoreMainPlugin
    from omnivore.file_type.plugin import FileTypePlugin
    from omnivore import get_image_path
    from omnivore.utils.jobs import get_global_job_manager

    # Include standard plugins
    core_plugins = [ CorePlugin(), OmnivoreTasksPlugin(), OmnivoreMainPlugin(), FileTypePlugin() ]
    if sys.platform == "darwin":
        from omnivore.framework.osx_plugin import OSXMenuBarPlugin
        core_plugins.append(OSXMenuBarPlugin())

    import omnivore.file_type.recognizers
    core_plugins.extend(omnivore.file_type.recognizers.plugins)

    import omnivore.plugins
    core_plugins.extend(omnivore.plugins.plugins)

    # Add the user's plugins
    core_plugins.extend(plugins)

    # Check basic command line args
    default_parser = argparse.ArgumentParser(description="Default Parser")
    default_parser.add_argument("--no-eggs", dest="use_eggs", action="store_false", default=True, help="Do not load plugins from python eggs")
    options, extra_args = default_parser.parse_known_args()

    # The default is to use the specified plugins as well as any found
    # through setuptools and any local eggs (if an egg_path is specified).
    # Egg/setuptool plugin searching is turned off by the use_eggs parameter.
    default = PluginManager(
        plugins = core_plugins,
    )
    if use_eggs and options.use_eggs:
        from pkg_resources import Environment, working_set
        from envisage.api import EggPluginManager
        from envisage.composite_plugin_manager import CompositePluginManager

        # Find all additional eggs and add them to the working set
        environment = Environment(egg_path)
        distributions, errors = working_set.find_plugins(environment)
        if len(errors) > 0:
            raise SystemError('cannot add eggs %s' % errors)
        logger = logging.getLogger()
        logger.debug('added eggs %s' % distributions)
        map(working_set.add, distributions)

        # The plugin manager specifies which eggs to include and ignores all others
        egg = EggPluginManager(
            include = [
                'omnivore.tasks',
            ]
        )

        plugin_manager = CompositePluginManager(
            plugin_managers=[default, egg]
        )
    else:
        plugin_manager = default

    # Add omnivore icons after all image paths to allow user icon themes to take
    # precidence
    from pyface.resource_manager import resource_manager
    import os
    image_paths = image_path[:]
    image_paths.append(get_image_path("icons"))
    image_paths.append(get_image_path("../omnivore8bit/icons"))
    resource_manager.extra_paths.extend(image_paths)

    from omnivore.templates import template_subdirs
    template_subdirs.extend(template_path)

    kwargs = {}
    if startup_task:
        kwargs['startup_task'] = startup_task
    if application_name:
        kwargs['name'] = application_name
    if document_class:
        kwargs['document_class'] = document_class

    # Create a debugging log
    if debug_log:
        filename = app.get_log_file_name("debug")
        handler = logging.FileHandler(filename)
        logger = logging.getLogger('')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    # Turn off omnivore log debug messages by default
    log = logging.getLogger("omnivore")
    log.setLevel(logging.INFO)

    # check for logging stuff again to pick up any new loggers loaded since
    # startup
    import omnivore.utils.wx.error_logger as error_logger
    if "-d" in extra_args:
        i = extra_args.index("-d")
        error_logger.enable_loggers(extra_args[i+1])
    app = FrameworkApplication(plugin_manager=plugin_manager, command_line_args=extra_args, **kwargs)

    app.run()

    job_manager = get_global_job_manager()
    if job_manager is not None:
        job_manager.shutdown()
