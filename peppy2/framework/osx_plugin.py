# Standard library imports.
import os
import wx

# Enthought library imports.
from traits.api import on_trait_change
from envisage.api import Plugin
from envisage.ui.tasks.api import TasksApplication
from pyface.api import FileDialog, YES, OK, CANCEL
from pyface.tasks.api import Task
from pyface.action.api import Action, MenuBarManager
from pyface.tasks.action.api import SMenuBar, SMenu, TaskActionManagerBuilder


class OpenAction(Action):
    name = 'Open'
    accelerator = 'Ctrl+O'
    tooltip = 'Open a file'

    def perform(self, event):
        print event
        print event.task
        print event.task.window
        print event.task.application
        dialog = FileDialog(parent=None)
        if dialog.open() == OK:
            event.task.application.load_file(dialog.path, event.task)

# These actions are temporarily duplicates of the actions in
# peppy2.framework.task -- need to figure out how to grab a selection of
# actions that apply to the Mac minimal menu
class ExitAction(Action):
    name = 'Quit'
    accelerator = 'Ctrl+Q'
    tooltip = 'Quit the program'
    menu_role = "Quit"

    def perform(self, event):
        event.task.exit()

class PreferencesAction(Action):
    name = 'Preferences...'
    tooltip = 'Program settings and configuration options'
    menu_role = "Preferences"

    def perform(self, event):
        print "peform: %s" % self.name

class AboutAction(Action):
    name = 'About...'
    tooltip = 'About this program'
    menu_role = "About"

    def perform(self, event):
        print "peform: %s" % self.name


class OSXMenuBarPlugin(Plugin):
    """Plugin providing the minimal menu when the Mac application has no
    windows open.
    """

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy2.framework.osx_menu'

    # The plugin's name (suitable for displaying to the user).
    name = 'OSX Menu'

    @on_trait_change('application:started')
    def set_common_menu(self):
        if hasattr(wx.MenuBar, "MacSetCommonMenuBar"):
            print "On OSX, have MacSetCommonMenuBar!!!"
            self.set_common_menu_29()
        else:
            print "Don't have MacSetCommonMenuBar!!!"

    def set_common_menu_29(self):
        menubar = SMenuBar(SMenu(OpenAction(),
                                 ExitAction(),
                                 id='File', name='&File'),
                           SMenu(PreferencesAction(),
                                 id='Edit', name='&Edit'),
                           SMenu(AboutAction(),
                                 id='Help', name='&Help'),
                           )
        app = wx.GetApp()
        # Create a fake task so we can use the menu creation routines
        task = Task(menu_bar=menubar)
        task.application = self.application
        
        t = TaskActionManagerBuilder(task=task)
        mgr = t.create_menu_bar_manager()
        control = mgr.create_menu_bar(app)
        wx.MenuBar.MacSetCommonMenuBar(control)
        
        # Need to create this dummy frame, otherwise wx will exit its event
        # loop when the last window is closed.
        self.dummy_frame = wx.Frame(None, -1, pos=(-9000,-9000))
        self.dummy_frame.Hide()
