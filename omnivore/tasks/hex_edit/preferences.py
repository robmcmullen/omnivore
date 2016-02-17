import sys

# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Dict, Enum, List, Str, Unicode, Int, Font, Range
from traitsui.api import FontEditor, HGroup, VGroup, Item, Label, \
    View, RangeEditor

if sys.platform == "darwin":
    def_font = "10 point Monaco"
elif sys.platform == "win32":
    def_font = "10 point Lucida Console"
else:
    def_font = "10 point monospace"


class HexEditPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.task.hex_edit'

    #### Preferences ##########################################################
    
    map_width_low = 1
    map_width_high = 256
    map_width = Range(low=map_width_low, high=map_width_high, value=16)
    
    bitmap_width_low = 1
    bitmap_width_high = 16
    bitmap_width = Range(low=bitmap_width_low, high=bitmap_width_high, value=1)

    # Font used for hex/disassembly
    text_font = Font(def_font)
    
    hex_grid_lower_case = Bool(True)
    
    assembly_lower_case = Bool(False)


class HexEditPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = HexEditPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    # Note the quirk in the RangeEditor: specifying a custom editor is
    # supposed to take the defaults from the item name specified, but I
    # can't get it to work with only the "mode" parameter.  I have to specify
    # all the other params, and the low/high values have to be attributes
    # in HexEditPreferences, not the values in the trait itself.  See
    # traitsui/editors/range_editor.py
    view = View(
        VGroup(HGroup(Item('map_width', editor=RangeEditor(mode="spinner", is_float=False, low_name='map_width_low', high_name='map_width_high')),
                      Label('Default Character Map Width (in bytes)'),
                      show_labels = False),
               HGroup(Item('bitmap_width', editor=RangeEditor(mode="spinner", is_float=False, low_name='bitmap_width_low', high_name='bitmap_width_high')),
                      Label('Default Bitmap Width (in bytes)'),
                      show_labels = False),
               HGroup(Item('text_font'),
                      Label('Hex Display Font'),
                      show_labels = False),
               HGroup(Item('hex_grid_lower_case'),
                      Label('Use Lower Case for Hex Digits'),
                      show_labels = False),
               HGroup(Item('assembly_lower_case'),
                      Label('Use Lower Case for Assembler Mnemonics'),
                      show_labels = False),
               label='Hex Editor'),
        resizable=True)
