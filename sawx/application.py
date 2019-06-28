""" Simple menubar & tabbed window framework
"""
import time
import argparse
import collections

import wx
import wx.adv

from .frame import SawxFrame
from .editor import get_editors, find_editor_class_by_id
from .filesystem import init_filesystems
from .filesystem import fsopen as open
from . import persistence
from .events import EventHandler
from .ui import error_logger
from .ui.prefs_dialog import PreferencesDialog
from .utils.background_http import BackgroundHttpDownloader
from . import errors
from .preferences import find_application_preferences

import logging
log = logging.getLogger(__name__)


class SawxApp(wx.App):
    app_name = "Sawx Framework"  # user visible application name

    default_uri = None  # when no files specified on the command line, will default to app_blank_uri

    app_version = "dev"

    app_description = "Sawx framework for wxPython applications"

    app_website = "http://playermissile.com/sawx"

    app_author = "Rob McMullen"

    app_icon = "icon://omnivore.ico"

    app_error_email_to = "feedback@playermissile.com"

    app_blank_page = f"""<html>
<h2>{app_name} {app_version}</h2>

<h3>{app_description}</h3>
"""

    app_blank_uri = "about://app"

    about_dialog_image = "omnivore256"

    about_dialog_credits = ""

    about_dialog_image_credits = f"""Images & Graphics:<ul>
<li>All the good looking icons are from <a href="https://icons8.com">icons8.com</a>
<li>I needed a few icons too esoteric for a design house, so I did create a few myself... and I'm not an artist. At all.
</ul>
"""

    default_editor = "simple_editor"

    command_line_args = None

    log_dir = ""

    log_file_ext = ".log"

    cache_dir = ""

    user_data_dir = ""

    next_document_id = 0

    documents = []

    clipboard_check_interval = .75

    toolbar_check_interval = .75

    window_sizes = {
        "default": [800, 600],
        "last_window_size": [1000, 800],
    }

    preferences_module = "sawx.preferences"

    _preferences = None

    in_bootup_process = True

    #### Initialization

    def OnInit(self):
        self.SetAppName(self.app_name)
        init_filesystems(self)
        persistence.setup_file_persistence(self.app_name)
        self.remember = persistence.restore_from_last_time()
        self.keybindings_changed_event = EventHandler(self)
        self.init_subprocesses()

        # Initialize dialog-based exception handler
        from .ui import exception_handler

        # Initialize dialog-based progress logger
        from .ui import progress_dialog
        progress_dialog.attach_handler()

        self.active_frame = None
        self.debug_show_focused = False
        self.last_clipboard_check_time = 0
        self.toolbar_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.deactivate_app_event = EventHandler(self)
        self.Bind(wx.EVT_ACTIVATE_APP, self.on_activate_app)

        return True

    def OnExit(self):
        persistence.remember_for_next_time(self.remember)
        self.shutdown_subprocesses()
        return wx.App.OnExit(self)

    def process_command_line_args(self, args):
        parser = argparse.ArgumentParser(description="Application parser")
        parser.add_argument("-t", "--task_id", "--task-id", "--edit_with","--edit-with", action="store", default="", help="Use the editing mode specified by this task id for all files listed on the command line")
        parser.add_argument("-d", "--debug_loggers", action="append", nargs=1, help="Comma separated list of debug loggers to enable")
        parser.add_argument("--show_editors", "--show-editors", action="store_true", default=False, help="List all task ids")
        parser.add_argument("--show_focused", "--show-focused", action="store_true", default=False, help="Show the focused window at every idle processing ")
        parser.add_argument("--show_prefs", "--show-prefs", action="store_true", default=False, help="Show the preferences dialog at start time")
        parser.add_argument("--build_docs", "--build-docs", action="store_true", default=False, help="Build documentation from the menubar")
        options, extra_args = parser.parse_known_args(args)
        if options.show_editors:
            for e in get_editors:
                print(f"{e.editor_id}: {e.ui_name}")
        if options.debug_loggers:
            for logger_name in options.debug_loggers:
                error_logger.enable_loggers(logger_name[0])
        task_arguments = collections.OrderedDict()
        if ":" in options.task_id:
            options.task_id, task_str = options.task_id.split(":", 1)
            items = task_str.split(",")
            for item in items:
                if '=' in item:
                    item, v = item.split('=', 1)
                else:
                    v = True
                task_arguments[item] = v
        log.debug("task arguments: %s" % task_arguments)
        try:
            default_editor = find_editor_class_by_id(options.task_id)()
        except errors.EditorNotFound:
            default_editor = None
        log.debug(f"default editor: {default_editor}")
        log.debug(f"args: {args}")

        if extra_args:
            log.debug(f"files to load: {extra_args}")
            frame = self.new_frame(uri=self.app_blank_uri)
            while len(extra_args) > 0:
                path = extra_args.pop(0)
                frame.load_file(path, default_editor, task_arguments, show_progress_bar=False)
        else:
            frame = self.new_frame()
        frame.Show()
        if options.show_prefs:
            wx.CallAfter(self.show_preferences_dialog, frame)
        wx.CallAfter(self.done_with_bootup)

    @classmethod
    def done_with_bootup(cls):
        log.debug("done_with_bootup")
        cls.in_bootup_process = False

    def MacOpenFiles(self, filenames):
        """OSX specific routine to handle files that are dropped on the icon
        
        """
        if self.command_line_args is not None:
            # MacOpenFiles gets called for command line arguments, so this flag
            # is used to detect real drops of files onto the dock icon.
            for filename in filenames:
                log.debug(f"MacOpenFiles: loading {filename}")
                self.tasks_application.load_file(filename, None)
        else:
            log.debug(f"MacOpenFiles: skipping {filenames} because it's a command line argument")

    #### Event handlers

    def on_idle(self, evt):
        if self.active_frame is not None:
            t = time.time()
            if t > self.last_clipboard_check_time + self.clipboard_check_interval:
                log.debug("checking clipboard")
                wx.CallAfter(self.active_frame.active_editor.idle_when_active)
                wx.CallAfter(self.active_frame.sync_can_paste)
                self.last_clipboard_check_time = time.time()
                if self.debug_show_focused:
                    self.show_focused()

    def activate_timer(self, start=True):
        if start:
            log.debug("restarting toolbar timer")
            wx.CallAfter(self.toolbar_timer.Start, self.toolbar_check_interval * 1000)
            log.debug("restarted toolbar timer")
        else:
            log.debug("halting toolbar timer")
            wx.CallAfter(self.toolbar_timer.Stop)
            log.debug("halted toolbar timer")

    def on_activate_app(self, evt):
        log.debug("on_activate_app")
        if evt.GetActive():
            self.activate_timer(True)
        else:
            self.activate_timer(False)
            log.debug("on_activate_app: deactivate!")
            self.deactivate_app_event(evt)

    def on_timer(self, evt):
        evt.Skip()
        if self.active_frame is not None:
            wx.CallAfter(self.active_frame.sync_active_tab)

    #### Shutdown

    def quit(self):
        frames_with_unsaved_stuff = []
        for frame in wx.GetTopLevelWindows():
            try:
                if frame.is_dirty:
                    frames_with_unsaved_stuff.append(frame)
            except AttributeError as e:
                pass
        if frames_with_unsaved_stuff:
            frame = frames_with_unsaved_stuff[0]
            if not frame.confirm("There is unsaved data.\n\nQuit anyway?", "Confirm Loss of Unsaved Data"):
                return

        self.activate_timer(False)
        for frame in wx.GetTopLevelWindows():
            log.debug(f"closing frame {frame}")
            try:
                frame.close_all_tabs()
            except AttributeError as e:
                log.error(f"error {e} closing {frame}")
        self.ExitMainLoop()

    #### Application information

    @classmethod
    def get_preferences(cls):
        if cls._preferences is None:
            cls._preferences = find_application_preferences(cls.preferences_module)
            cls._preferences.restore_user_settings()
        return cls._preferences

    @property
    def preferences(self):
        return self.get_preferences()

    @property
    def about_image_bitmap(self):
        data = open(self.about_image, 'rb')
        image = wx.Image(data)
        return wx.Bitmap(image)

    @property
    def about_dialog_html(self):
        return f"""<html>
<body text="#ffffff" bgcolor="#222255" link="#aaaaaa" vlink="#ff0000" alink="#000088">

<h2>{self.app_name} {self.app_version}</h2>

<h3>{self.app_description}</h3>

<p>by {self.app_author} <a href="{self.app_website}">{self.app_website}</a>

<p>using {self.about_dialog_system_versions}

<p>{self.about_dialog_credits}

<p>{self.about_dialog_image_credits}
</html>
"""

    @property
    def about_dialog_system_versions(self):
        import sys
        major, minor, micro = sys.version_info[0:3]
        desc = f"Python {major}.{minor}.{micro}:\n<ul>"
        import wx
        desc += "<li>wxPython %s\n" % wx.version()
        try:
            import sawx
            desc += "<li>sawx %s\n" % sawx.__version__
        except:
            pass
        try:
            import numpy
            desc += "<li>numpy %s\n" % numpy.version.version
        except:
            pass
        try:
            import OpenGL
            import OpenGL.GL as gl
            desc += "<li>PyOpenGL %s\n" % OpenGL.__version__
            desc += "<li>OpenGL %s\n" % gl.glGetString(gl.GL_VERSION).encode('utf-8')
            desc += "<li>OpenGL Vendor: %s\n" % gl.glGetString(gl.GL_VENDOR).encode('utf-8')
            desc += "<li>OpenGL Renderer: %s\n" % gl.glGetString(gl.GL_RENDERER).encode('utf-8')
            desc += "<li>GLSL primary: %s\n" % gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).encode('utf-8')
            num_glsl = gl.glGetInteger(gl.GL_NUM_SHADING_LANGUAGE_VERSIONS)
            desc += "<li>GLSL supported: "
            for i in range(num_glsl):
                v = gl.glGetStringi(gl.GL_SHADING_LANGUAGE_VERSION, i).encode('utf-8')
                desc += v + ", "
            desc += "\n"
        except:
            pass
        try:
            import gdal
            desc += "<li>GDAL %s\n" % gdal.VersionInfo()
        except:
            pass
        try:
            import pyproj
            desc += "<li>PyProj %s\n" % pyproj.__version__
        except:
            pass
        try:
            import netCDF4
            desc += "<li>netCDF4 %s\n" % netCDF4.__version__
        except:
            pass
        try:
            import shapely
            desc += "<li>Shapely %s\n" % shapely.__version__
        except:
            pass
        try:
            import omnivore_framework
            desc += "<li>Omnivore %s\n" % omnivore_framework.__version__
        except:
            pass
        desc += "</ul>"
        return desc

    def show_about_dialog(self):
        from .ui.dialogs import SawxAboutDialog
        SawxAboutDialog.show_or_raise()

    def show_preferences_dialog(self, parent, page_name=None):
        dialog = PreferencesDialog(parent, page_name)
        dialog.ShowModal()

    #### Convenience functions

    @property
    def last_window_size(self):
        return self.window_sizes["last_window_size"]

    @last_window_size.setter
    def last_window_size(self, value):
        value = list(value)
        log.debug(f"new window size: {value}")
        self.window_sizes["last_window_size"] = value

    def new_frame(self, uri=None):
        if uri is None:
            uri = self.default_uri
        if uri is None:
            uri = self.app_blank_uri
        frame = SawxFrame(None, uri)
        return frame

    def show_focused(self):
        focused = self.active_frame.FindFocus()
        print(f"Focus at: {focused}" + focused.GetName() if focused is not None else "")

    #### subprocess helpers

    def init_subprocesses(self):
        self.downloader = None

    def shutdown_subprocesses(self):
        if self.downloader:
            self.downloader.stop_threads()

    def get_downloader(self):
        if self.downloader is None:
            self.downloader = BackgroundHttpDownloader()
        return self.downloader


def restore_from_last_time():
    log.debug("Restoring window sizes")
    cls = wx.GetApp().__class__
    cls.window_sizes = persistence.get_json_data("window_sizes", cls.window_sizes)


def remember_for_next_time():
    log.debug("Remembering window sizes")
    persistence.save_json_data("window_sizes", wx.GetApp().window_sizes)
