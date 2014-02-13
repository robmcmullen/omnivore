"""Sample panes for Text Editor

"""
# Enthought library imports.
from pyface.api import PythonEditor
from pyface.tasks.api import TaskPane
from traits.api import Instance


class PythonEditorPane(TaskPane):
    """ A wrapper around the Pyface Python editor.
    """

    #### TaskPane interface ###################################################

    id = 'example.python_editor_pane'
    name = 'Python Editor'

    #### PythonEditorPane interface ###########################################

    editor = Instance(PythonEditor)

    ###########################################################################
    # 'ITaskPane' interface.
    ###########################################################################

    def create(self, parent):
        self.editor = PythonEditor(parent)
        self.control = self.editor.control

    def destroy(self):
        self.editor.destroy()
        self.control = self.editor = None
