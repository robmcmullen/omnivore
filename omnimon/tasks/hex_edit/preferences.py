# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Dict, Enum, List, Str, Unicode, Int, Font
from traitsui.api import FontEditor, HGroup, VGroup, Item, Label, \
    View


class HexEditPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnimon.task.hex_edit'

    #### Preferences ##########################################################

    # Font used for hex/disassembly
    text_font = Font('10 point fixed')


class HexEditPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = HexEditPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    view = View(
        VGroup(HGroup(Item('text_font'),
                      Label('Hex Display Font'),
                      show_labels = False),
               label='Hex Editor'),
        resizable=True)
