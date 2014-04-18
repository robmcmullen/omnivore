# Standard library imports.
import os
import wx

# Enthought library imports.
from traits.api import on_trait_change
from envisage.api import Plugin
from envisage.ui.tasks.api import TasksApplication
from pyface.api import FileDialog, YES, OK, CANCEL
from pyface.tasks.api import Task, TaskWindow
from pyface.action.api import Action, MenuBarManager
from pyface.tasks.action.api import SMenuBar, SMenu, TaskActionManagerBuilder

from peppy2.framework.actions import OpenAction, ExitAction, PreferencesAction, AboutAction


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
        app = wx.GetApp()
        app.tasks_application = self.application
        print app

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
        window = TaskWindow(application=self.application)
        task = Task(menu_bar=menubar, window=window)
        
        t = TaskActionManagerBuilder(task=task)
        mgr = t.create_menu_bar_manager()
        control = mgr.create_menu_bar(app)
        wx.MenuBar.MacSetCommonMenuBar(control)
        
        # Prevent wx from exiting when the last window is closed
        app.SetExitOnFrameDelete(False)

    @on_trait_change('application:application_exiting')
    def kill_wx(self):
        app = wx.GetApp()
        app.ExitMainLoop()
