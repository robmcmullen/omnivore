# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Dict, Enum, List, Str, Unicode
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, \
    View


class TextEditPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.framework.text_edit'

    #### Preferences ##########################################################

    # Display line numbers
    show_line_numbers = Bool

    # Wrap lines (if True) or display horizontal scrollbar (if False)
    wrap_lines = Bool


class TextEditPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = TextEditPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    view = View(
        VGroup(HGroup(Item('show_line_numbers'),
                      Label('Show line numbers'),
                      show_labels = False),
               HGroup(Item('wrap_lines'),
                      Label('Wrap lines'),
                      show_labels = False),
               label='Text editor'),
        resizable=True)
