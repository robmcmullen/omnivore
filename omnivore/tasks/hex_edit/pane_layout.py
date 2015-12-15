"""Sample panes for HexEdit

"""
# Enthought library imports.
from pyface.tasks.api import TaskLayout, PaneItem, HSplitter, VSplitter

import panes


# The project ID must be changed when the pane layout changes, otherwise
# the new panes won't be displayed because the previous saved state of the
# application will be loaded.  Changing the project ID forces the framework to
# honor the new layout, because there won't be a saved state of this new ID.

# The saved state is stored in ~/.config/Omnivore/tasks/wx/application_memento

# Removing this file will cause the default layout to be used.  The saved state
# is only updated when quitting the application; if the application is killed
# (or crashes!) the saved state is not updated.

task_id_with_pane_layout = 'omnivore.hex_edit.v1'

def pane_layout():
    """ Create the default task layout, which is overridded by the user's save
    state if it exists.
    """
    return TaskLayout(
        left=VSplitter(
            PaneItem('hex_edit.segments'),
            PaneItem('hex_edit.undo'),
        ),
        right=HSplitter(
            PaneItem('hex_edit.disasmbly_pane'),
            PaneItem('hex_edit.font_map'),
            PaneItem('hex_edit.byte_graphics'),
            ),
        bottom=HSplitter(
            PaneItem('hex_edit.memory_map'),
            ),
        )

def pane_create():
    """ Create all the pane objects available for the task (regardless
    of visibility -- visibility is handled in the task activation method
    MaproomTask.activated)
    """
    return [
        panes.DisassemblyPane(),
        panes.ByteGraphicsPane(),
        panes.FontMapPane(),
        panes.MemoryMapPane(),
        panes.SegmentsPane(),
        panes.UndoPane(),
        ]
