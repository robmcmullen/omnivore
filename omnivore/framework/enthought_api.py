

# Enthought library imports.
from envisage.ui.tasks.api import TaskWindow
from pyface.action.api import Action, ActionItem, Group
from pyface.tasks.api import Task
from pyface.tasks.action.api import TaskActionManagerBuilder, TaskActionController
from traits.api import Instance, Callable, Event, Str, List, Any, Property, cached_property, on_trait_change, Undefined

from .editor import FrameworkEditor

import logging
log = logging.getLogger(__name__)


BENCHMARK_OLD = False
if not BENCHMARK_OLD:
    # These are new implementations of actions that use far fewer traits than
    # the default enthought ones. The drawback is, of course, they aren't
    # updated the instant their dynamic trait is updated. The menu_update_event
    # on the Task object should be set during idle handling to update the menu.

    log.debug("BENCHMARKING THE FRAMEWORK ACTIONS!")
    class BasicFrameworkAction(Action):

        ##### Class attributes

        class DummyTask(Task):
            menu_update_event = Event
            active_editor = None

        dummy_task = DummyTask()

        ##### Traits

        # The Task with which the action is associated. Set by the framework.
        task = Instance(Task)

        @property
        def object(self):
            return None

        @property
        def active_editor(self):
            if self.task is not None:
                return self.task.active_editor
            return None

        ##### Protected interface.

        def _get_attr(self, obj, name, default=None):
            try:
                for attr in name.split('.'):
                    # Perform the access in the Trait name style: if the object
                    # is None, assume it simply hasn't been initialized and
                    # don't show the warning.
                    if obj is None:
                        return default
                    else:
                        obj = getattr(obj, attr)
            except AttributeError:
                if obj is Undefined or obj is None:
                    pass
                else:
                    log.error("Did not find name %r on %r" % (attr, obj))
                return default
            return obj

        ##### Action interface

        def destroy(self):
            # Disconnect listeners to task and dependent properties. Use the
            # dummy task instead of None so the intermediate trait handler
            # task.menu_update_event on on_dynamic_menu_update below won't
            # barf. Since it depends on self.task, it gets notified when
            # self.task changes, and if it gets set to None it gets called,
            # resulting in the error because it can't find the
            # menu_update_event on None.
            self.task = self.dummy_task

    class EnabledFrameworkAction(BasicFrameworkAction):
        # trait on the task that is used to set the enabled/disabled state.
        # Can't change dynamically; for efficiency purposes, the enabled name
        # as set at creation time will be used for the life of the action.
        #
        # Popup enable/checked state can be handled differently by defining the
        # methods _update_popup_enabled and _update_popup_checked. Those
        # methods take a single argument containing the popup data (the same
        # popup data as supplied to popup_context_menu_from_actions). The
        # enabled and checked state falls back to the _update_enabled and
        # _update_checked if the popup-specific methods are not supplied.
        enabled_name = Str("")

        @on_trait_change('task.menu_update_event')
        def on_dynamic_menu_update(self, ui_state):
            if ui_state is Undefined:
                return
            if self.active_editor:
                self._update_enabled(ui_state)
                self._update_checked(ui_state)
            self.on_dynamic_menu_update_hook(ui_state)
            log.debug("on_dynamic_menu_update %s: %s" % (self, self.enabled))

        def on_dynamic_menu_update_hook(self, evt):
            pass

        def on_popup_menu_update(self, ui_state, popup_data):
            try:
                self._update_popup_enabled(ui_state, popup_data)
            except AttributeError:
                self._update_enabled(ui_state)
            try:
                self._update_popup_checked(ui_state, popup_data)
            except AttributeError:
                self._update_checked(ui_state)
            log.debug("on_popup_menu_update %s: %s" % (self, self.enabled))

        def _update_enabled(self, ui_state):
            if self.enabled_name and ui_state:
                enabled = bool(self._get_attr(ui_state, self.enabled_name, None))
                if enabled is None:
                    log.warning("%s flag does not exist in ui_state object %s" % (self.enabled_name, ui_state))
                    enabled = False
                self.enabled = enabled
            else:
                self.enabled = bool(self.task)

        def _update_checked(self, ui_state):
            pass


    class NameChangeAction(EnabledFrameworkAction):
        menu_item_name = Str

        default_name = Str("-no event-")

        def on_dynamic_menu_update_hook(self, evt):
            if self.menu_item_name:
                if self.active_editor:
                    self.name = str(self._get_attr(self.active_editor,
                                                   self.menu_item_name, '0'))
                else:
                    self.name = getattr(self, 'default_name', '1')
            else:
                self.name = getattr(self, 'default_name', '2')
            log.debug("on_dynamic_menu_update_hook %s: %s" % (self.name, self.menu_item_name))

    EditorAction = EnabledFrameworkAction

if BENCHMARK_OLD:
    log.warning("BENCHMARKING THE ENTHOUGHT EDITOR ACTIONS!")
    from pyface.tasks.action.api import EditorAction
    FrameworkAction = EditorAction

    class IndividualTraitEventNonWorkingFrameworkAction(Action):
        # NOTE: this doesn't work, but I'm saving it in case I want to try
        # again with this method.


        # The Task with which the action is associated. Set by the framework.
        task = Instance(Task)

        # The active editor in the central pane with which the action is associated.
        active_editor = Property(Instance(FrameworkEditor),
                             depends_on='task.active_editor')

        # trait on the task that is used to set the enabled/disabled state.
        # Can't change dynamically; for efficiency purposes, the enabled name
        # as set at creation time will be used for the life of the action.
        enabled_name = Str("")

        ##### Protected interface.

        @cached_property
        def _get_active_editor(self):
            if self.task is not None:
                return self.task.active_editor
            return None

        def _get_attr(self, obj, name, default=None):
            try:
                for attr in name.split('.'):
                    # Perform the access in the Trait name style: if the object
                    # is None, assume it simply hasn't been initialized and
                    # don't show the warning.
                    if obj is None:
                        return default
                    else:
                        obj = getattr(obj, attr)
            except AttributeError:
                log.error("Did not find name %r on %r" % (attr, obj))
                return default
            return obj

        ##### Trait change handlers

        def _task_changed(self, old, new):
            method = getattr(self, '_enabled_update')
            name = getattr(self, 'enabled_name')
            print "ACTIVE", name, self.active_editor
            if name:
                if hasattr(self.active_editor, name):
                    name = "active_editor." + name
                    if old:
                        old.on_trait_change(method, name, remove=True)
                    if new:
                        new.on_trait_change(method, name)
                    print "ADDED ENABLED_NAME %s TO %s" % (name, self.active_editor)
            method()

        def _enabled_update(self):
            if self.enabled_name:
                if self.task:
                    self.enabled = bool(self._get_attr(self.active_editor, self.enabled_name, False))
                else:
                    self.enabled = False
            else:
                self.enabled = bool(self.task)
            print "ENABLING %s: %s" % (self.name, self.enabled)

        @property
        def object(self):
            return None

        # @property
        # def active_editor(self):
        #     if self.task is not None:
        #         return self.task.active_editor
        #     return None

        def destroy(self):
            # Disconnect listeners to task and dependent properties.
            self.task = None


    class EditorAction(EnabledFrameworkAction):
        pass


    class NameChangeAction(EditorAction):
        """Extension to the EditorAction that provides a user-updatable menu item
        name based on a trait
        
        EditorAction is subclassed from ListeningAction, and the ListeningAction
        methods destroy and _object_chaged must be called because the new
        trait name 'menu_item_name' can't be added to list of traits managed by
        ListeningAction and so must be taken care of here before the superclass
        can do its work.
        """
        menu_item_name = Str

        def destroy(self):
            """ Called when the action is no longer required.

            Remove all the task listeners.

            """

            if self.object:
                self.object.on_trait_change(
                    self._menu_item_update, self.menu_item_name, remove=True
                )
            super(NameChangeAction, self).destroy()

        def _menu_item_name_changed(self, old, new):
            obj = self.object
            if obj is not None:
                if old:
                    obj.on_trait_change(self._menu_item_update, old, remove=True)
                if new:
                    obj.on_trait_change(self._menu_item_update, new)
            self._label_update()

        def _object_changed(self, old, new):
            kind = 'menu_item'
            method = getattr(self, '_%s_update' % kind)
            name = getattr(self, '%s_name' % kind)
            if name:
                if old:
                    old.on_trait_change(method, name, remove=True)
                if new:
                    new.on_trait_change(method, name)
            method()
            super(NameChangeAction, self)._object_changed(old, new)

        def _menu_item_update(self):
            if self.menu_item_name:
                if self.object:
                    self.name = str(self._get_attr(self.object,
                                                   self.menu_item_name, 'Undo'))
                else:
                    self.name = getattr(self, 'default_name', 'Undo')
            else:
                self.name = getattr(self, 'default_name', 'Undo')


class BaseDynamicSubmenuGroup(Group):
    """ A group used for a dynamic menu.
    """

    #### 'ActionManager' interface ############################################

    id = 'DynamicMenuGroup'
    items = List

    #### 'TaskChangeMenuManager' interface ####################################

    # The ActionManager to which the group belongs.
    manager = Any

    # ENTHOUGHT QUIRK: This doesn't work: can't have a property depending on
    # a task because this forces task_default to be called very early in the
    # initialization process, before the window hierarchy is defined.
    #
    # active_editor = Property(Instance(IEditor),
    #                         depends_on='task.active_editor')

    event_name = Str('change this to the Event trait')

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        # Override this in your subclass to return the list of actions
        return []

    def _rebuild(self, new_trait_val):
        # Clear out the old group, then build the new one.
        self.destroy()

        # Get the new items, passing the event arguments to the method
        self.items = self._get_items(new_trait_val)

        # Set up parent so that radio items can determine their siblings to
        # uncheck others when checked. (see the _checked_changed method in
        # pyface/ui/wx/action/action_item.py)
        for item in self.items:
            item.parent = self

        # Inform our manager that it needs to be rebuilt.
        self.manager.changed = True

    #### Trait initializers ###################################################

    def _items_default(self):
        log.debug("DYNAMICGROUP: _items_default!!!")
        t = self._get_trait_for_event()
        t.on_trait_change(self._rebuild, self.event_name)
        return self._get_items()

    def _get_trait_for_event(self):
        raise NotImplementedError

    def _manager_default(self):
        manager = self
        while isinstance(manager, Group):
            manager = manager.parent
        log.debug("DYNAMICGROUP: _manager_default=%s!!!" % manager)
        return manager

    # ENTHOUGHT QUIRK: This doesn't work: the trait change decorator never
    # seems to get called, however specifying the on_trait_change in the
    # _items_default method works.
    #
    #    @on_trait_change('task.layer_selection_changed')
    #    def updated_fired(self, event):
    #        log.debug("SAVELAYERGROUP: updated!!!")
    #        self._rebuild(event)


class TaskDynamicSubmenuGroup(BaseDynamicSubmenuGroup):
    """ A group used for a dynamic menu.
    """

    # The task instance must be passed in as an attribute creation argument
    # because we need to bind on a task trait change to update the menu
    task = Instance('omnivore.framework.task.FrameworkTask')

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_trait_for_event(self):
        return self.task

    #### Trait initializers ###################################################

    def _task_default(self):
        log.debug("DYNAMICGROUP: _task_default=%s!!!" % self.manager.controller.task)
        return self.manager.controller.task


class ApplicationDynamicSubmenuGroup(BaseDynamicSubmenuGroup):
    """ A group used for a dynamic menu based on an application event.
    """

    # The application instance must be a trait so we can set an on_trait_change
    # handler
    application = Instance('envisage.ui.tasks.api.TasksApplication')

    def _get_trait_for_event(self):
        return self.application

    #### Trait initializers ###################################################

    def _application_default(self):
        log.debug("DYNAMICGROUP: _application_default=%s!!!" % self.manager.controller.task.window.application)
        return self.manager.controller.task.window.application


class FrameworkTaskActionController(TaskActionController):
    # The whole point of this class is to redefine these two methods so that
    # the framework's custom action can have a task assigned to it. The parent
    # TaskActionController specifically checks for a TaskAction, which is the
    # problem. TaskActions subclass from (a few parents up) ListeningAction,
    # which is where I think the problem is where hundreds of thousands of
    # trait listener callbacks occur.
    def add_to_menu(self, item):
        """ Called when an action item is added to a menu/menubar.
        """
        action = item.item.action
        if hasattr(action, 'task'):
            action.task = self.task

    def add_to_toolbar(self, item):
        """ Called when an action item is added to a toolbar.
        """
        action = item.item.action
        if hasattr(action, 'task'):
            action.task = self.task


class FrameworkTaskActionManagerBuilder(TaskActionManagerBuilder):
    # Intercept the task action controller factory
    def _controller_default(self):
        return FrameworkTaskActionController(task=self.task)


class FrameworkTaskWindow(TaskWindow):
    # The only purpose of this is to override the envisage TaskWindow to
    # intercept the action manager builder factory so the framework can provide
    # its own.
    action_manager_builder_factory = Callable(FrameworkTaskActionManagerBuilder)
