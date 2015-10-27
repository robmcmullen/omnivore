import os

# Enthought library imports.
from traits.api import Any, Bool, Unicode, Property
from pyface.tasks.api import Editor

from document import Document


class FrameworkEditor(Editor):
    """The pyface editor template for the omnimon framework
    
    The abstract methods 
    """

    #### 'IProjectEditor' interface ############################################

    document = Any(None)
    
    name = Property(Bool, depends_on='document')

    tooltip = Property(Unicode, depends_on='document')
    
    dirty = Property(Bool, depends_on='document')  # has to be a property because pyface's Editor uses it.
    
    can_undo = Bool(False)  # has to be a property of Editor because EditorActions need to refer to this trait
    
    undo_label = Unicode("Undo")
    
    can_redo = Bool(False)
    
    redo_label = Unicode("Redo")
    
    printable = Bool(False)

    #### trait default values

    def _document_default(self):
        return Document()

    #### property getters

    def _get_name(self):
        return self.document.name

    def _get_tooltip(self):
        return self.document.metadata.uri

    def _get_dirty(self):
        return self.document.undo_stack.is_dirty()

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def create(self, parent):
        """ Creates the toolkit-specific control for the widget.
        """
        raise NotImplementedError

    def load(self, guess=None, **kwargs):
        """ Loads the contents of the editor.
        """
        raise NotImplementedError

    def view_of(self, editor, **kwargs):
        """ Copy the view of the supplied editor.
        """
        raise NotImplementedError

    def save(self, path=None):
        """ Saves the contents of the editor.
        """
        raise NotImplementedError

    def undo(self):
        """ Undoes the last action
        """
        raise NotImplementedError

    def redo(self):
        """ Re-performs the last undone action
        """
        raise NotImplementedError
    
    def print_preview(self):
        raise NotImplementedError
    
    def print_page(self):
        raise NotImplementedError
    
    def save_as_pdf(self, path=None):
        raise NotImplementedError
    
    def update_history(self):
        pass

    #### convenience functions
    
    @property
    def task(self):
        return self.editor_area.task
    
    @property
    def window(self):
        return self.editor_area.task.window

    @property
    def most_recent_path(self):
        return os.path.dirname(self.document.uri)
