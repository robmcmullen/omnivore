""" Simple menubar & tabbed window framework
"""
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

    default_uri = "about://app"  # when no files specified on the command line

    app_version = "dev"

    app_description = "Sawx framework for wxPython applications"

    app_website = "http://playermissile.com/sawx"

    app_icon = "icon://omnivore.ico"

    app_error_email_to = "feedback@playermissile.com"

    about_uri = "about://app"  # for Help->About menu item

    about_image = "icon://omnivore256.png"  # for Help->About menu item

    about_html = f"""<html>
<h2>{app_name} {app_version}</h2>

<h3>{app_description}</h3>

<p><img src="{about_image}">
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

    window_sizes = {
        "default": [800, 600],
        "last_window_size": [1000, 800],
    }

    preferences_module = "sawx.preferences"

    _preferences = None

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
        self.Bind(wx.EVT_IDLE, self.on_idle)
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
            frame = self.new_frame(uri=self.about_uri)
            while len(extra_args) > 0:
                path = extra_args.pop(0)
                frame.load_file(path, default_editor, task_arguments, show_progress_bar=False)
        else:
            frame = self.new_frame()
        frame.Show()
        if options.show_prefs:
            wx.CallAfter(self.show_preferences_dialog, frame)

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
            self.active_frame.active_editor.idle_when_active()

    #### Shutdown

    def quit(self):
        for frame in wx.GetTopLevelWindows():
            log.debug(f"closing frame {frame}")
            try:
                if frame.is_dirty:
                    log.warning(f"frame {frame} has unsaved changes")
            except AttributeError as e:
                log.error(f"error {e} closing {frame}")
            else:
                frame.close_all_tabs()
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

    def show_about_dialog(self):
        info = wx.adv.AboutDialogInfo()

        # Load the image to be displayed in the about box.
        #image = self.about_image.create_image()
        icon = wx.Icon()
        try:
            icon.CopyFromBitmap(self.about_image_bitmap)
            info.SetIcon(icon)
        except:
            log.error("AboutDialog: bad icon file: %s" % self.about_image)

        info.SetName(self.app_name)
        info.SetVersion(self.app_version)
        info.SetDescription(self.app_description)
        info.SetWebSite(self.app_website)

        dialog = wx.adv.AboutBox(info)

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
        frame = SawxFrame(None, uri)
        return frame

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
