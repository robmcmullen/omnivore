=================
Menus and Actions
=================

The platform specific menu/toolbar stuff is located in pyface/pyface/ui/wx/action

Actions that are put into groups are sorted.  The sort routines
are based on "before" and "after" From the description in
pyface/pyface/tasks/topological_sort.py:

    Sort a sequence of items with 'before', 'after', and 'id' attributes.
        
    The sort is topological. If an item does not specify a 'before' or 'after',
    it is placed after the preceding item.

    If a cycle is found in the dependencies, a warning is logged and the order
    of the items is undefined.


Adding to Existing Menus
========================

Using the SchemaAddition it seems to be possible to add to menus. SchemaAdditions also have an 'absolute_position' trait which can be either 'first' or 'last': 

    The action appears at the absolute specified position first or last.
    This is useful for example to keep the File menu the first menu in a
    menubar, the help menu the last etc.  If multiple actions in a schema have
    absolute_position 'first', they will appear in the same order specified;
    unless 'before' and 'after' traits are set to sort these multiple items.
    This trait takes precedence over 'after' and 'before', and values of those
    traits that are not compatible with the absolute_position are ignored.

In a task, adding menu items is provide by the extra_actions trait, e.g.::

    def _extra_actions_default(self):
        actions = [ SchemaAddition(id='NewView',
                                   factory=NewViewAction,
                                   path='MenuBar/Window'),
                    ]
        return actions


Menu Item Enabled State
=======================

Subclassing from EditorAction provides the ability to set the enabled/disabled state of the item based on a trait in the parent Editor.  E.g.::

    class SaveAction(EditorAction):
        enabled_name = 'dirty'

will automatically enable/disable the item whenever the state of
task.active_editor.dirty changes.


Menu Item Initial Value
=======================

Checkboxes and toggles require an initial value, and also must be updated when
the view or the active editor changes.  My naive approach to handling this
problem is to add a trait change handler on the EditorAction's active editor
trait, e.g.  setting a checkbox initial state::

    @on_trait_change('active_editor')
    def _update_checked(self):
        self.checked = self.active_editor.control.bounding_boxes_shown
