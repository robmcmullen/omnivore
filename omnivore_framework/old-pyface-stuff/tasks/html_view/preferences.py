# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Str, Int
from traitsui.api import HGroup, VGroup, Item, Label, \
    View


class HtmlViewPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.tasks.htmlview'

    #### Preferences ##########################################################

    # Font name for normal (proportional spacing) rendering
    normal_face = Str("")

    # Font name for monospace rendering
    fixed_face = Str("")

    # Default font size
    font_size = Int(10)


class HtmlViewPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = HtmlViewPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    view = View(
        VGroup(HGroup(Item('normal_face'),
                      Label('Proportional Font Name'),
                      show_labels = False),
               HGroup(Item('fixed_face'),
                      Label('Fixed Width Font Name'),
                      show_labels = False),
               HGroup(Item('font_size'),
                      Label('Default Point Size'),
                      show_labels = False),
               label='HTML Viewer'),
        resizable=True)
