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

# Enthought library imports.
from traits.api import Any, HasTraits, List, Property, Str, Unicode, Int
from pyface.action.api import StatusBarManager

class FrameworkStatusBarManager(StatusBarManager):
    """ A status bar manager realizes itself in a status bar control. """

    # The message displayed in the first field of the status bar.
    message = Unicode

    # The message to be displayed in debug field of the status bar
    debug = Unicode
    
    debug_width = Int(200)

    # The toolkit-specific control that represents the status bar.
    status_bar = Any

    ###########################################################################
    # 'StatusBarManager' interface.
    ###########################################################################

    def create_status_bar(self, parent):
        """ Creates a status bar. """

        if self.status_bar is None:
            self.status_bar = wx.StatusBar(parent)
            self.status_bar._pyface_control = self
            self.status_bar.SetFieldsCount(2)
            self.status_bar.SetStatusWidths([-1, self.debug_width])
            self.status_bar.SetStatusText(self.message, 0)
            self.status_bar.SetStatusText(self.debug, 1)

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

    def _debug_changed(self):
        """ Sets the text displayed on the status bar. """

        if self.status_bar is not None:
            self.status_bar.SetStatusText(self.debug, 1)

        return
