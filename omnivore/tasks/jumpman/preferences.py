# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Int, Dict, Enum, List, Str, Unicode, Range
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, \
    View, RangeEditor


class JumpmanPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.tasks.jumpman_edit'

    #### Preferences ##########################################################

    # Width of bitmap in bytes
    bitmap_width_low = 1
    bitmap_width_high = 256
    bitmap_width = Range(low=bitmap_width_low, high=bitmap_width_high, value=1)


class JumpmanPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = JumpmanPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    # See note in tasks/hex_edit/preferences.py regarding RangeEditor
    view = View(
        VGroup(HGroup(Item('bitmap_width', editor=RangeEditor(mode="spinner", is_float=False, low_name='bitmap_width_low', high_name='bitmap_width_high')),
                      Label('Default Bitmap Width (in bytes)'),
                      show_labels = False),
               label='Bitmap Editor'),
        resizable=True)
