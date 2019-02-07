""" Simple menubar & tabbed window framework
"""
import wx
import wx.adv

from .frame import OmnivoreFrame
from .editor import find_editor_class_by_name
from .filesystem import init_filesystems
from .filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


class OmnivoreApp(wx.App):
    app_name = "Omnivore Framework"  # user visible application name

    about_version = "1.0"

    about_description = "Omnivore framework for wxPython applications"

    about_website = "http://playermissile.com/omnivore"

    about_image = "icon://omnivore256.png"

    about_html = f"""<html>
<h2>{app_name} {about_version}</h2>

<h3>{about_description}</h3>

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

    default_window_size = (800, 600)

    last_window_size = None

    #### Initialization

    def OnInit(self):
        self.SetAppName(self.app_name)
        self.init_class_attrs()
        init_filesystems(self)
        return True

    @classmethod
    def init_class_attrs(cls):
        """Initialize all application class attributes from default values.

        This is called during the OnInit processing, before any configuration files
        are read, in order to provide sane default in case configuration files don't
        yet exist.
        """
        if cls.last_window_size is None:
            cls.last_window_size = cls.default_window_size

    #### Shutdown

    def shutdown_subprocesses(self):
        pass

    def quit(self):
        for frame in wx.GetTopLevelWindows():
            try:
                if frame.is_dirty:
                    print(f"frame {frame} has unsaved changes")
            except AttributeError:
                pass
        self.shutdown_subprocesses()
        self.ExitMainLoop()

    #### Mac-specific hooks

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

    #### Application information

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
        info.SetVersion(self.about_version)
        info.SetDescription(self.about_description)
        info.SetWebSite(self.about_website)

        dialog = wx.adv.AboutBox(info)

    #### Convenience functions

    def new_frame(self, editor=None):
        if editor is None:
            editor = find_editor_class_by_name("title_screen")()
        frame = OmnivoreFrame(editor)
        return frame

