# Standard library imports.
import sys

# Major package imports.
import wx
import wx.html

# Enthought library imports.
from traits.api import Bool, Event, Instance, File, Unicode, Property, provides

# Local imports.
from omnivore.framework.editor import FrameworkEditor

import logging
log = logging.getLogger(__name__)


class HtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, prefs):
        log.debug("calling HtmlWindow constructor")
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        log.debug("setting HtmlWindow fonts")
        self.SetStandardFonts(prefs.font_size, prefs.normal_face, prefs.fixed_face)

    def OnCellMouseHover(self, cell, x, y):
        # Without access to the task window, search the control hierarchy to
        # find a wx.Frame and set the status text directly
        parent = self.GetParent()
        while parent:
            if hasattr(parent, "SetStatusText"):
                linkinfo = cell.GetLink()
                if linkinfo is not None:
                    parent.SetStatusText(linkinfo.GetHref())
                else:
                    parent.SetStatusText("")
                return
            parent = parent.GetParent()


class HtmlViewer(FrameworkEditor):
    """ The toolkit specific implementation of a simple HTML viewer
    """

    #### Events ####

    changed = Event

    ###########################################################################
    # 'PythonEditor' interface.
    ###########################################################################

    def create(self, parent):
        self.control = self._create_control(parent)

    def rebuild_document_properties(self):
        text = self.document.to_bytes()
        self.control.SetPage(text)

    def set_preferences(self):
        prefs = self.task.preferences
        self.control.SetStandardFonts(prefs.font_size, prefs.normal_face, prefs.fixed_face)

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        log.debug("creating HtmlWindow")
        self.control = HtmlWindow(parent, self.task.preferences)
        #self.set_preferences()

        log.debug("loading HtmlWindow")
        # Load the editor's contents.
        self.load()

        return self.control
