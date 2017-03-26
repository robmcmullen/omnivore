# Standard library imports.
import sys
from os.path import basename

# Major package imports.
import wx

# Enthought library imports.
from traits.api import Bool, Event, Instance, File, Unicode, Property, provides
from pyface.tasks.api import Editor

# Local imports.
from omnivore.framework.editor import FrameworkEditor
from i_image_editor import IImageEditor
from omnivore.utils.wx.imagescroller import ImageScroller


@provides(IImageEditor)
class ImageEditor(FrameworkEditor):
    """ The toolkit specific implementation of a ImageEditor.  See the
    IImageEditor interface for the API documentation.
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
    # 'ImageEditor' interface.
    ###########################################################################

    def create(self, parent):
        self.control = self._create_control(parent)

    def rebuild_document_properties(self):
        pass

    def copy_view_properties(self, old_editor):
        pass

    def rebuild_ui(self):
        self.reconfigure_panes()

    def reconfigure_panes(self):
        self.control.recalc_view()

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
        self.control = ImageScroller(parent, self.task)

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################
