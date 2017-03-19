"""Sample panes for JumpmanEdit

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

task_id_with_pane_layout = 'omnivore.jumpman.v3'

def pane_layout():
    """ Create the default task layout, which is overridded by the user's save
    state if it exists.
    """
    return TaskLayout(
        left=VSplitter(
            PaneItem('jumpman.segments'),
            PaneItem('jumpman.undo'),
        ),
        right=HSplitter(
            PaneItem('jumpman.sidebar'),
            VSplitter(
                PaneItem('jumpman.level_data'),
                PaneItem('jumpman.hex'),
                PaneItem('jumpman.triggers'),
                ),
        ),
        )

def pane_create():
    """ Create all the pane objects available for the task (regardless
    of visibility -- visibility is handled in the task activation method
    MaproomTask.activated)
    """
    return [
        panes.SegmentsPane(),
        panes.UndoPane(),
        panes.HexPane(),
        panes.SidebarPane(),
        panes.LevelDataPane(),
        panes.TriggerPane(),
        ]

def pane_initially_visible():
    """ List of initial pane visibility.  Any panes not listed will use the
    last saved state.
    """
    
    return {
        'jumpman.hex': False,
        }
