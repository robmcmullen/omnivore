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

Adding a group (i.e. multiple actions) seems to be a bit finicky about how they are added. Key points:

1) the menu specified must already exist or the items will be silently ignored
2) the only way that worked for me was to specify the group in a lambda:

        testgroup = lambda : Group(ZoomInAction(),
                          ZoomOutAction(), id="zoomgroup2234")
        actions = [SchemaAddition(factory=testgroup,
                                   path='MenuBar/Extra',
                                   absolute_position="first",
                                   ),
                    ]

Attempting to define a group like this:

class ZoomGroup(Group):
    id = "ZoomGroup"
    
    def _items_default(self):
        return [ZoomInAction(),
                ZoomOutAction()]

and using

        actions = [SchemaAddition(factory=ZoomGroup,
                                   path='MenuBar/Extra',
                                   absolute_position="first",
                                   ),
                    ]

silently failed.


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


Tool Bars and Enable/Visible states
===================================

I added some code in pyface to set toolbar item visibily and (entire) toolbar
visibility.  Apparently they don't work together well when using the agw.aui
toolbar.

.. note::

    None of this is applicable to the standard wx.Toolbar, although the
    wx.Toolbar has problems on Mac, which is why I needed to go with the
    owner- drawn agw.aui toolbar.

I added an action with a 'visible_name' attribute, e.g.::

    class AddLinesAction(EditorAction):
        name = 'Add Lines Mode'
        visible_name = 'layer_has_points'
        tooltip = 'Add lines to the current layer'
        image = ImageResource('add_lines.png')
        style = 'radio'

and when using the aui toolbar, the initial toolbar view could contain two
checked items.  Once the toolbar was hidden and shown, it would appear
correctly.

I instrumented pyface/ui/wx/application_window.py _wx_show_tool_bar as follows::

    def _wx_show_tool_bar(self, tool_bar, visible):
        """ Hide/Show a tool bar. """

        if aui is not None:
            pane = self._aui_manager.GetPane(tool_bar.tool_bar_manager.id)

            if visible:
                pane.Show()

            else:
                # Without this workaround, toolbars know the sizes of other
                # hidden toolbars and leave gaps in the toolbar dock
                pane.window.Show(False)
                self._aui_manager.DetachPane(pane.window)
                info = self._get_tool_par_pane_info(pane.window)
                info.Hide()
                self._aui_manager.AddPane(pane.window, info)

            self._aui_manager.Update()
            if visible:
                tool_bar.tool_bar_manager._wx_fix_tool_state(tool_bar)

        else:
            tool_bar.Show(visible)

        return

and added the following method to ToolBarManager in
pyface/ui/wx/action/toolbar_manager.py::

    def _wx_fix_tool_state(self, tool_bar):
        """ Workaround for the wxPython tool bar bug.

        Without this,  only the first item in a radio group can be selected
         when the tool bar is first realised 8^()

        """

        for group in self.groups:
            for item in group.items:
                if item.action.style == 'radio':
                    print "action %s, state %s, internal state %s, %s" % (item.action.name, item.action.checked, item.control_id, str(item))
                    for wrapped in item._wrappers:
                        print " wrapped control: %s, state=%s" % (wrapped.control, wrapped.control.state)
                        wrapped.control.state = 0
                        tool_bar.ToggleTool(wrapped.control_id, item.action.checked)

which worked around the problem.

I subsequently discovered that if you don't hide the toolbar items of toolbars
that you plan to hide, it works correctly.

