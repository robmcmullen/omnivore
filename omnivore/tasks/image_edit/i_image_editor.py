""" A widget for displaying bitmapped images. """


# Enthought library imports.
from traits.api import Bool, Event, Instance, File, Interface, Unicode
from pyface.tasks.i_editor import IEditor


class IImageEditor(IEditor):
    """ A widget for editing text. """

    #### 'IPythonEditor' interface ############################################

    # Object being editor is a file
    obj = Instance(File)

    # The pathname of the file being edited.
    path = Unicode

    #### Events ####

    # The contents of the editor has changed.
    changed = Event

    ###########################################################################
    # 'IPythonEditor' interface.
    ###########################################################################

    def load(self, path=None):
        """ Loads the contents of the editor. """

    def save(self, path=None):
        """ Saves the contents of the editor. """
