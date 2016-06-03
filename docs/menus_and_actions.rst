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


Menu Bar Manager
================

Found this useful tidbit in pyface/pyface/tasks/tests/test__dock_pane_toggle_group.py:

        # Fish the dock pane toggle group from the menu bar manager.
        dock_pane_toggle_group = []
        def find_doc_pane_toggle(item):
            if item.id == 'tests.bogus_task.DockPaneToggleGroup':
                dock_pane_toggle_group.append(item)

        self.task_state.menu_bar_manager.walk(find_doc_pane_toggle)

        self.dock_pane_toggle_group = dock_pane_toggle_group[0]



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

Dynamically Populated Menus
===========================

There are two ways include menus that can have varying numbers of items, either
as a list in the same menu or as a list in a pop-right submenu.  Both are
accomplished in the same manner using pyface menu Groups; the latter is simply
placed in a sub-menu.

I modified the example found in pyface/tasks/action/task_toggle_group.py to
walk the list of Tasks known to the application and add an item to the menu
for each task that supports opening a new blank file of that type::

    class NewFileAction(Action):
        """ An action for creating a new empty file that can be edited by a particular task
        """
        tooltip = Property(Unicode, depends_on='name')

        task_cls = Any
        
        def perform(self, event=None):
            event.task.new_window(task=self.task_cls)

        def _get_tooltip(self):
            return u'Open a new %s' % self.name

    class NewFileGroup(Group):
        """ A menu for creating a new file for each type of task
        """

        #### 'ActionManager' interface ############################################

        id = 'NewFileGroup'
        
        items = List

        #### 'TaskChangeMenuManager' interface ####################################

        # The ActionManager to which the group belongs.
        manager = Any

        # The window that contains the group.
        application = Instance('envisage.ui.tasks.api.TasksApplication')
            
        ###########################################################################
        # Private interface.
        ###########################################################################

        def _get_items(self):
            items = []
            for factory in self.application.task_factories:
                if hasattr(factory.factory, 'new_file_text'):
                    task_cls = factory.factory
                    if task_cls.new_file_text:
                        action = NewFileAction(name=task_cls.new_file_text, task_cls=task_cls)
                        items.append((task_cls.new_file_text, ActionItem(action=action)))
            items.sort()
            items = [i[1] for i in items]
            return items

        def _rebuild(self):
            # Clear out the old group, then build the new one.
            self.destroy()
            self.items = self._get_items()

            # Inform our manager that it needs to be rebuilt.
            self.manager.changed = True
            
        #### Trait initializers ###################################################

        def _items_default(self):
            self.application.on_trait_change(self._rebuild, 'task_factories[]')
            return self._get_items()

        def _manager_default(self):
            manager = self
            while isinstance(manager, Group):
                manager = manager.parent
            return manager
        
        def _application_default(self):
            return self.manager.controller.task.window.application

The menu can be added to the menubar either directly::

    def _menu_bar_default(self):
        return SMenuBar(SMenu(NewFileGroup(),
                              ...

or in a submenu::

    def _menu_bar_default(self):
        return SMenuBar(SMenu(Separator(id="NewGroup", separator=False),
                              SMenu(NewFileGroup(), id="NewFileGroup", name="New", before="NewGroupEnd", after="NewGroup"),
                              Separator(id="NewGroupEnd", separator=False),
                              ...

but note that to workaround a problem that caused the NewFileGroup to show up
at the end of the file menu, I had to add these dummy separator groups and
force the NewFileGroup to be between them.  Placing the NewFileGroup as the
first group or not including BOTH the before and after keywords caused the
NewFileGroup to appear at the end of the menu.


Groups
======

Within a menu::

    SMenu(
        Group(
            UseFontAction(font=fonts.A8DefaultFont),
            id="a1", separator=True),
        FontChoiceGroup(id="a2", separator=True),
        Group(
            LoadFontAction(),
            GetFontFromSelectionAction(),
            id="a3", separator=True),
        id='FontChoiceSubmenu', name="Font"),

items appear to be sorted by their id, NOT the order in the argument list, so
specifying the id explicitly is the only way to force the sort order to match
the listing order.


Submenu Names
=============

It is not obvious how to dynamically rename a submenu, because submenu names
must be defined in the SMenu call, as above.  A trait change handler in a
Group that sets the Group name does not work as that's not propagated to the
toolkit-specific menu.  It turns out that you have to set the changed trait
on the pyface.ui.wx.action.menu_manager.MenuManager object in the manager
hierarchy of the group.  A manager is the pyface object that performs the
MVC handling of the menu system -- pyface menu objects aren't directly UI
components themselves, they use the manager to create the wx side of the menu.
In this example::
    
    class NewViewInGroup(TaskDynamicSubmenuGroup):
        name = 'New View As'
        tooltip = 'New view of the project with a different task'
        event_name = 'document_changed'

        def perform(self, event):
            event.task.new_window(view=event.task.active_editor)
        
        @on_trait_change('task.document_changed')
        def _update_name(self):
            if self.task.active_editor:
                self.manager.name = "New View of %s" % self.task.active_editor.document.name
                print "manager", self.manager
                print "parent", self.manager.parent
                print "parent.parent", self.manager.parent.parent
                self.manager.parent.parent.changed = True

it turns out the MenuManager is the grandparent of the Group.


Keyboard Mapping
================

One of the big attractions/headaches in peppy1 was its ability to handle emacs-
style multi-key shortcuts.  It was a big project to be able to do that, and I'm
not sure how to handle it in envisage.

Possibly with accelerator tables, explained better than I had seen before here:

http://wxpython-users.1045709.n5.nabble.com/Use-of-AcceleratorTable-td2337246.html

although I do remember experimenting with them in the peppy1 days without
success.  I don't remember if I tried the methods recommended above and they
didn't work, or if I just didn't understand them correctly.

Also: see the Phoenix docs for an event processing overview. Does this apply to 2.x?

http://wxpython.org/Phoenix/docs/html/events_overview.html

Or maybe EventFilter?

http://wxpython.org/Phoenix/docs/html/EventFilter.html
