# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory, TasksApplication
from apptools.preferences.api import PreferencesHelper
from traits.api import on_trait_change, Bool, Dict, Enum, List, Str, Unicode, Instance, Any
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, \
    View
from envisage.api import IApplication
from pyface.api import Dialog, OK


class FrameworkPreferenceDialog(Dialog):

    application = Instance(IApplication)

    def _create_dialog_area(self, parent):
        from envisage.ui.tasks.preferences_dialog import \
            PreferencesDialog

        dialog = self.application.get_service(PreferencesDialog)
        self.prefs_ui = dialog.edit_traits(parent=parent, scrollable=True, kind='subpanel')
        return self.prefs_ui.control

    @on_trait_change('closed')
    def delete_prefs_ui(self):
        if self.return_code == OK:
            self.prefs_ui.handler.apply()
            self.application.preferences.save()
        self.prefs_ui.finish()
        self.prefs_ui = None


class FrameworkPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # Enthought bug? The application trait is needed to provide subclasses a
    # way to find application level defaults, like user config directories.
    # But, if I declare this to be a trait, upon assignment in
    # FrameworkApplication.get_preferences, the FrameworkApplication instance
    # gets converted to unicode.
    #
    # application = Any

    # Instead, use a class attribute because the application object won't
    # change so there's no need to make it an instance attribute.
    application = None

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.framework'

    #### Preferences ##########################################################

    # The task to activate on app startup if not restoring an old layout.
    default_task = Str

    # Whether to always apply the default application-level layout.
    # See TasksApplication for more information.
    always_use_default_layout = Bool


class FrameworkPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = FrameworkPreferences

    #### 'FrameworkPreferencesPane' interface ################################

    task_map = Dict(Str, Unicode)

    view = View(
        VGroup(HGroup(Item('always_use_default_layout'),
                      Label('Always use the default active task on startup'),
                      show_labels = False),
               HGroup(Label('Default active task:'),
                      Item('default_task',
                           editor=EnumEditor(name='handler.task_map')),
                      enabled_when = 'always_use_default_layout',
                      show_labels = False),
               label='Application startup'),
        resizable=True)

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _task_map_default(self):
        return dict((factory.id, factory.name)
                    for factory in self.dialog.application.task_factories)
