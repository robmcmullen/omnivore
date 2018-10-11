#------------------------------------------------------------------------------
#
#  Copyright (c) 2005, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#
#  Author: Enthought, Inc.
#
#------------------------------------------------------------------------------

""" A status bar manager realizes itself in a status bar control.
"""

# Major package imports.
import wx
from wx.lib.stattext import GenStaticText  # standard static text can't set background color on some platforms

# Enthought library imports.
from traits.api import Any, Unicode, Int, Float, Bool, Event
from pyface.action.api import StatusBarManager


class FrameworkStatusBar(wx.StatusBar):
    """A custom status bar for displaying the application version in the bottom
    right corner."""

    def __init__(self, parent, widths, error_delay):
        wx.StatusBar.__init__(self, parent, -1)
        self.error_delay = error_delay

        self.SetFieldsCount(len(widths))
        self.SetStatusWidths(widths)

        self.field_widths = list(widths)
        self.error_control = GenStaticText(self, -1)
        self.error_control.Hide()
        self.message_expire_time = 0
        self.reposition_controls()

        self.expire_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.expire_timer)
        self.Bind(wx.EVT_SIZE, self.on_size)

        f = self.GetFont()
        self.error_control.SetFont(wx.Font(f.GetPointSize(), f.GetFamily(),
                                 f.GetStyle(), wx.BOLD, f.GetUnderlined(),
                                 f.GetFaceName(), f.GetEncoding()))
        self.error_control.SetForegroundColour((255, 255, 255))
        self.error_control.SetBackgroundColour((211, 72, 54))

    def on_size(self, event):
        self.reposition_controls()

    def on_timer(self, event):
        self.error_control.Hide()

    def reposition_controls(self):
        rect = self.GetFieldRect(0)
        self.error_control.SetRect(rect)

    def show_error(self, text):
        self.error_control.SetLabel(" " + text)
        rect = self.GetFieldRect(0)
        self.error_control.SetRect(rect)
        self.error_control.Show()
        self.expire_timer.Start(self.error_delay * 1000, oneShot=True)


class FrameworkStatusBarManager(StatusBarManager):
    """ A status bar manager realizes itself in a status bar control. """

    # The message displayed in the first field of the status bar.
    message = Unicode

    message_width = Int(600)

    # The message to be displayed in debug field of the status bar
    command_help = Unicode

    command_help_width = Int(-1)

    # The message to be displayed in debug field of the status bar
    debug = Unicode

    debug_width = Int(200)

    # An error message to be displayed in the first field, and also for a
    # minimum time
    error = Event

    # Number of seconds to display an error message before the status bar is
    # freed up for normal messages
    error_delay = Int(3)

    # The toolkit-specific control that represents the status bar.
    status_bar = Any

    ###########################################################################
    # 'StatusBarManager' interface.
    ###########################################################################

    def create_status_bar(self, parent):
        """ Creates a status bar. """

        if self.status_bar is None:
            self.status_bar = FrameworkStatusBar(parent, [self.message_width, self.command_help_width, self.debug_width], self.error_delay)
            self.status_bar._pyface_control = self
            self.status_bar.SetStatusText(self.message, 0)
            self.status_bar.SetStatusText(self.command_help, 1)
            self.status_bar.SetStatusText(self.debug, 2)

        return self.status_bar

    def remove_status_bar(self, parent):
        """ Creates a status bar. """

        if self.status_bar is not None:
            self.status_bar.Destroy()
            self.status_bar._pyface_control = None
            self.status_bar = None

    ###########################################################################
    # Trait event handlers.
    ###########################################################################

    def _message_changed(self):
        """ Sets the text displayed on the status bar. """

        if self.status_bar is not None:
            self.status_bar.SetStatusText(self.message, 0)

        return

    def _command_help_changed(self):
        """ Sets the text displayed on the status bar. """

        if self.status_bar is not None:
            self.status_bar.SetStatusText(self.command_help, 1)

        return

    def _debug_changed(self):
        """ Sets the text displayed on the status bar. """

        if self.status_bar is not None:
            self.status_bar.SetStatusText(self.debug, 2)

        return

    def _error_fired(self, message):
        """Displays an error message and doesn't allow the status bar to be
        updated until a minimum time passes.
        """
        self.status_bar.show_error(message)
