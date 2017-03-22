# Standard library imports.
import os

import wx

# Enthought library imports.
from pyface.tasks.api import DockPane
from traits.api import Event, File, List, Str


class FileBrowserPane(DockPane):
    """ A simple file browser pane.
    """

    #### TaskPane interface ###################################################

    id = 'omnivore.framework.file_browser_pane'
    name = 'File Browser'

    #### FileBrowserPane interface ############################################

    # The list of wildcard filters for filenames.
    filters = List(Str)

    def create_contents(self, parent):
        control = wx.GenericDirCtrl(parent, -1, size=(200,-1), style=wx.NO_BORDER)
        control.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_selected)
        return control

    def on_selected(self, evt):
        selected_file = self.control.GetFilePath()
        if selected_file:
            wx.CallAfter(self.task.window.application.load_file, selected_file, self.task, in_current_window=True)
        else:
            # blank file path means that a directory was double-clicked instead
            # of a file.  Skipping the event will expand the directory.
            evt.Skip()


class PythonScriptBrowserPane(FileBrowserPane):
    """ A file browser pane restricted to Python scripts.
    """

    #### TaskPane interface ###################################################

    id = 'omnivore.framework.python_script_browser_pane'
    name = 'Script Browser'

    #### FileBrowserPane interface ############################################

    filters = [ '*.py' ]
