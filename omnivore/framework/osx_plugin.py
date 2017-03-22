# Standard library imports.
import os
import wx

# Enthought library imports.
from traits.api import on_trait_change, List, Instance
from envisage.api import Plugin, ExtensionPoint
from envisage.ui.tasks.api import TasksApplication
from pyface.api import FileDialog, YES, OK, CANCEL
from pyface.tasks.api import Task, TaskWindow
from pyface.action.api import Action, ActionItem, Group, Separator
from pyface.tasks.action.api import SMenuBar, SMenu, TaskActionManagerBuilder, SchemaAddition

from omnivore.framework.actions import OpenAction, ExitAction, PreferencesAction, AboutAction
from omnivore.framework.task import FrameworkTask

import logging
log = logging.getLogger(__name__)


class OSXMinimalTask(FrameworkTask):
    @classmethod
    def can_edit(cls, mime):
        return False


class OSXMenuBarPlugin(Plugin):
    """Plugin providing the minimal menu when the Mac application has no
    windows open.
    """

    OSX_MINIMAL_MENU = 'omnivore.osx_minimal_menu'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore.framework.osx_menu'

    # The plugin's name (suitable for displaying to the user).
    name = 'OSX Menu'

    #### Extension points offered by this plugin ##############################

    minimal_menu_actions = ExtensionPoint(
        List(Instance(SchemaAddition)), id=OSX_MINIMAL_MENU, desc="""
    
    This extension point allows you to contribute schema additions to the menu
    that will appear when no windows are open in an Mac OS X application.
    
        """
    )

    @on_trait_change('application:started')
    def set_common_menu(self):
        if hasattr(wx.MenuBar, "MacSetCommonMenuBar"):
            self.set_common_menu_29()

    def set_common_menu_29(self):
        menubar = SMenuBar(SMenu(Separator(id="NewGroup", separator=False),
                                 Separator(id="NewGroupEnd", separator=False),
                                 Group(OpenAction(), id="OpenGroup"),
                                 Separator(id="OpenGroupEnd", separator=False),
                                 Separator(id="SaveGroupEnd", separator=False),
                                 Group(ExitAction(), id="ExitGroup"),
                                 id='File', name='&File'),
                           SMenu(PreferencesAction(),
                                 id='Edit', name='&Edit'),
                           SMenu(AboutAction(),
                                 id='Help', name='&Help'),
                           )
        app = wx.GetApp()
        # Create a fake task so we can use the menu creation routines
        window = TaskWindow(application=self.application)
        log.debug("OSXMenuBarPlugin: minimal menu extra items: %s" % str(self.minimal_menu_actions))
        task = OSXMinimalTask(menu_bar=menubar, window=window, extra_actions=self.minimal_menu_actions)

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
