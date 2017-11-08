# Standard library imports.
import os

# Enthought library imports.
from traits.api import HasTraits, on_trait_change, Any, Instance, List, Bool, Int, Range, Str, Unicode, Event
from apptools.preferences.api import PreferencesHelper
from envisage.ui.tasks.api import PreferencesPane, TaskExtension
from envisage.api import ExtensionPoint, Plugin
from pyface.action.api import Action, ActionItem, Group, Separator
from pyface.tasks.action.api import SMenu, TaskAction, EditorAction, SchemaAddition
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, View

from omnivore.framework.plugin import FrameworkPlugin
from omnivore.framework.actions import ApplicationDynamicSubmenuGroup

import logging
log = logging.getLogger(__name__)


class OpenRecentPreferences(PreferencesHelper):
    """ The preferences helper for the Framework application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'open_recent'

    #### Preferences ##########################################################

    # Controls where the new files are added: top or bottom
    add_at_top = Bool(True)

    list_max = 50 # not a trait, can't seem to programmically pull out the max value of the range object

    # Maximum number of files to retain in the list
    list_length = Range(low=4, high=list_max, value=10)

    def max_list_length(self):
        # No easy way to get the maximum value of a Range object
        t = self.trait('list_length')
        values = t.full_info(None, None, None).split()
        return int(values[-1])


class OpenRecentPreferencesPane(PreferencesPane):
    """ The preferences pane for the Framework application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = OpenRecentPreferences

    #### 'FrameworkPreferencesPane' interface ################################

    view = View(
        VGroup(HGroup(Item('list_length'),
                      Label('Number of recent files to remember'),
                      show_labels = False),
               HGroup(Item('add_at_top'),
                      Label('Add new file to top of list'),
                      show_labels = False),
               label='Open Recent'),
        resizable=True)

# FIXME: RecentFiles doesn't work as a traits object! Weird.
#
#class RecentFiles(HasTraits):
#    """Open a file from the list of recently opened files.
#
#    Maintains a list of the most recently opened files so that the next time
#    you start the application you can see what you were editing last time.
#    This list is automatically maintained, so every time you open a new file,
#    it is added to the list.  This list is limited in size by the classpref
#    'list_length' in L{RecentFilesPlugin}.
#    """
#
#    # Preferences aren't duplicated here; instead, reference the helper so they
#    # can be lookup up every time they are needed.
#    helper = Instance(OpenRecentPreferences)
#
#    # location to serialize the list to persist across application runs
#    serialize_uri = Unicode
#
#    storage_flag = Bool
#
#    updated = Event


class RecentFiles(object):
    """Open a file from the list of recently opened files.
    
    Maintains a list of the most recently opened files so that the next time
    you start the application you can see what you were editing last time.
    This list is automatically maintained, so every time you open a new file,
    it is added to the list.  This list is limited in size by the classpref
    'list_length' in L{RecentFilesPlugin}.
    """

    def __init__(self, helper, serialize_uri):
        self.helper = helper
        self.serialize_uri = serialize_uri
        self._storage_flag_default()

    #### Trait initializers ###################################################

    def _storage_flag_default(self):
        self.storage_flag = True
        self.storage = []
        log.debug("STORAGE_FLAG!!! %s" % self.storage_flag)
        self.unserialize()

    def is_acceptable_uri(self, uri):
        # skip files with the about: protocol
        #return uri.scheme != 'about' and uri.scheme != 'mem'
        return True

    def iter_items(self):
        for item in self.storage[0:self.helper.list_length]:
            yield item

    def serialize(self):
        """Serialize the current items to the file"""
        log.debug("SERIALIZING: %s" % str(self.storage))
        # trim list to maximum possible length
        self.storage[self.helper.max_list_length():] = []
        with open(self.serialize_uri,'w') as fh:
            try:
                for item in self.iter_items():
                    fh.write("%s%s" % (item.encode('utf8'),os.linesep))
            except:
                pass

    def unserialize(self):
        """Unserialize items from the file into a list"""
        log.debug("UNSERIALIZING: %s" % str(self.serialize_uri))
        self.storage = []
        try:
            with open(self.serialize_uri,'r') as fh:
                for line in fh:
                    trimmed = line.decode('utf8').rstrip()
                    if trimmed.strip():
                        self.storage.append(trimmed)
        except:
            pass

    def append_uri(self, uri, extra=None):
        if self.is_acceptable_uri(uri):
            item = unicode(uri)
            if extra:
                item = (item, extra)
            # if we're adding an item that's already in the list, move it
            # to the top of the list by recreating the list
            try:
                index = self.storage.index(item)
                self.storage.pop(index)
            except ValueError:
                pass
            # New items are added at the top of this list
            self.storage[0:0]=[item]
            self.serialize()
        log.debug("STORAGE: %s" % str(self.storage))


class OpenRecentAction(Action):
    """This submenu contain a list of the files most recently loaded or saved.

    You can limit the number of items to remember in the General tab of the
    `Preferences`_ dialog.
    """
    doc_hint = "summary"

    uri = Unicode

    def _name_default(self):
        return self.uri

    def perform(self, event):
        event.task.window.application.load_file(self.uri, event.task)


class OpenRecentGroup(ApplicationDynamicSubmenuGroup):
    """ A menu for creating a new file for each type of task
    """

    #### 'ActionManager' interface ############################################

    id = 'NewFileGroup'

    event_name = 'plugin_event'

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _get_items(self, event_data=None):
        items = []
        recent_files = self.application.get_plugin_data('open_recent')
        log.debug("GET ITEMS: recent_files=%s, storage=%s" % (recent_files, recent_files.storage))
        if recent_files is not None:
            for uri in recent_files.iter_items():
                action = OpenRecentAction(uri=uri)
                items.append(ActionItem(action=action))

        return items


class OpenRecentPlugin(FrameworkPlugin):

#    recent_files = None

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'open_recent'

    # The plugin's name (suitable for displaying to the user).
    name = 'Recently Opened Files List'

    # Extension point IDs.
    PREFERENCES_PANES = 'envisage.ui.tasks.preferences_panes'
    TASK_EXTENSIONS   = 'envisage.ui.tasks.task_extensions'
    OSX_MINIMAL_MENU = 'omnivore.osx_minimal_menu'

    #### Contributions to extension points made by this plugin ################

    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    actions = List(contributes_to=TASK_EXTENSIONS)
    osx_actions = List(contributes_to=OSX_MINIMAL_MENU)

    def _osx_actions_default(self):
        submenu = lambda: SMenu(
            id='OpenRecentSubmenu', name="Open Recent"
        )
        actions = [
            SchemaAddition(factory=submenu,
                           path='MenuBar/File',
                           after="OpenGroup", before="OpenGroupEnd",
                           ),
            SchemaAddition(id='OpenRecent',
                           factory=OpenRecentGroup,
                           path='MenuBar/File/OpenRecentSubmenu'),
            ]

        return actions

    def _actions_default(self):
        # Using the same actions as the minimal menu
        actions = self._osx_actions_default()
        return [ TaskExtension(actions=actions) ]

    def _preferences_panes_default(self):
        return [ OpenRecentPreferencesPane ]

    def start(self):
        helper = self.get_helper(OpenRecentPreferences)

        # self.home is the config directory created especially for this plugin!
        recent_files = RecentFiles(helper=helper,
                                   serialize_uri=os.path.join(self.home, "files.dat"))
        self.set_plugin_data(recent_files)

    @on_trait_change('application:successfully_loaded_event,application:successfully_saved_event')
    def update_recent_file(self, uri):
        log.debug("RECENT FILE: %s" % uri)
        recent_files = self.get_plugin_data()
        try:
            recent_files.append_uri(uri)
        except Exception, e:
            log.warning("FAILED ADDING %s to recent files list: %s" % (uri, e.message))
            return
        self.fire_plugin_event()
