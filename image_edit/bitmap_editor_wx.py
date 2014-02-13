# Standard library imports.
import sys
from os.path import basename

# Major package imports.
import wx

# Enthought library imports.
from traits.api import Bool, Event, Instance, File, Unicode, Property, provides
from pyface.tasks.api import Editor

# Local imports.
from i_bitmap_editor import IBitmapEditor
from utils.wx.bitmapscroller import BitmapScroller

@provides(IBitmapEditor)
class BitmapEditor(Editor):
    """ The toolkit specific implementation of a BitmapEditor.  See the
    IBitmapEditor interface for the API documentation.
    """

    #### 'IPythonEditor' interface ############################################

    obj = Instance(File)

    path = Unicode

    dirty = Bool(False)

    name = Property(Unicode, depends_on='path')

    tooltip = Property(Unicode, depends_on='path')

    #### Events ####

    changed = Event

    def _get_tooltip(self):
        return self.path

    def _get_name(self):
        return basename(self.path) or 'Untitled'

    ###########################################################################
    # 'BitmapEditor' interface.
    ###########################################################################

    def create(self, parent):
        self.control = self._create_control(parent)

    def load(self, guess=None):
        """ Loads the contents of the editor.
        """
        img = wx.EmptyImage(1,1)
        if guess is None:
            path = self.path
        else:
            metadata = guess.get_metadata()
            path = metadata.uri
            if not img.LoadMimeStream(guess.get_stream(), metadata.mime):
                #raise TypeError("Bad image -- either it really isn't an image, or wxPython doesn't support the image format.")
                img = wx.EmptyImage(1,1)

        print img
        self.control.setImage(img)
        self.dirty = False

    def save(self, path=None):
        """ Saves the contents of the editor.
        """
        if path is None:
            path = self.path

        self.control.saveImage(path)

        self.dirty = False

    ###########################################################################
    # Trait handlers.
    ###########################################################################

    def _path_changed(self):
        if self.control is not None:
            self.load()

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.control = BitmapScroller(parent)

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################

