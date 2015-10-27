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

    # Command processor

    def update_undo_redo(self):
        command = self.document.undo_stack.get_undo_command()
        if command is None:
            self.undo_label = "Undo"
            self.can_undo = False
        else:
            text = str(command).replace("&", "&&")
            self.undo_label = "Undo: %s" % text
            self.can_undo = True
            
        command = self.document.undo_stack.get_redo_command()
        if command is None:
            self.redo_label = "Redo"
            self.can_redo = False
        else:
            text = str(command).replace("&", "&&")
            self.redo_label = "Redo: %s" % text
            self.can_redo = True
        self.dirty = self.document.undo_stack.is_dirty()
    
    def undo(self):
        undo = self.document.undo_stack.undo(self)
        self.process_flags(undo.flags)
        self.update_undo_redo()
    
    def redo(self):
        undo = self.document.undo_stack.redo(self)
        self.process_flags(undo.flags)
        self.update_undo_redo()
    
    def process_flags(self, flags):
        self.update_history()

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
