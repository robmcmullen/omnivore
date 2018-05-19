# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane, TaskFactory
from apptools.preferences.api import PreferencesHelper
from traits.api import Bool, Dict, Enum, List, Str, Unicode
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, \
    View


class ImageEditPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'omnivore.framework.image_edit'

    #### Preferences ##########################################################

    # Scale image to fit window when initially loaded
    fit_image_on_load = Bool


class ImageEditPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = ImageEditPreferences

    category = Str('Editors')

    #### 'FrameworkPreferencesPane' interface ################################

    view = View(
        VGroup(HGroup(Item('fit_image_on_load'),
                      Label('Scale image to window on initial load'),
                      show_labels = False),
               label='Image editor'),
        resizable=True)
