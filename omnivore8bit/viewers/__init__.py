import uuid

import wx

from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined
from envisage.api import ExtensionPoint

from omnivore.framework.plugin import FrameworkPlugin
from ..byte_edit.linked_base import LinkedBase
import omnivore.framework.actions as fa
from ..byte_edit import actions as ba
from ..byte_edit.commands import PasteCommand
from ..arch import fonts

from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges

from omnivore8bit.arch.machine import Machine, Atari800
from omnivore8bit.utils import searchutil

import logging
log = logging.getLogger(__name__)


class SegmentViewer(HasTraits):
    """Base class for any viewer window that can display (& optionally edit)
    the data in a segment

    Linked base exists for the lifetime of the viewer. If the user wants to
    change the base, a new viewer is created and replaces this viewer.
    """
    ##### class attributes

    name = "_base_"

    pretty_name = "_base_"

    has_editable_bytes = True  # directly user-editable bytes

    has_bitmap = False

    has_font = False  # uses the bitmapped font to display characters

    has_colors = False  # uses machine colors to display stuff

    has_cpu = False

    has_hex = False

    has_text_font = False  # uses the app-wide text font

    has_metadata_only = False

    valid_mouse_modes = []  # toolbar description

    copy_special = []  # additional copy functions available when viewer is present

    searchers = [  # BaseSearcher classes that are applicable to this viewer
        searchutil.HexSearcher,
        searchutil.CommentSearcher,
    ]

    ##### Traits

    uuid = Str

    linked_base = Instance(LinkedBase)

    machine = Instance(Machine)

    control = Any(None)

    pane_info = Any(None)

    range_processor = Property(Any, depends_on='control')

    supported_clipboard_data_objects = List

    antic_font = Any(transient=True)

    blinking_antic_font = Any(transient=True)

    #### Default traits

    def _uuid_default(self):
        return str(uuid.uuid4())

    def _machine_default(self):
        return Atari800.clone_machine()

    def _supported_clipboard_data_objects_default(self):
        return [a[0] for a in self.supported_clipboard_data_object_map.values()]

    ##### Properties

    @property
    def segment(self):
        return self.linked_base.segment

    @property
    def editor(self):
        return self.linked_base.editor

    @property
    def preferences(self):
        return self.linked_base.cached_preferences

    ##### Class methods

    @classmethod
    def create_control(cls, parent, linked_base):
        raise NotImplementedError("Implement in subclass!")

    @classmethod
    def check_name(cls, name):
        return name == cls.name

    @classmethod
    def create(cls, parent, linked_base, machine=None, uuid=None):
        control = cls.create_control(parent, linked_base)
        v = cls(linked_base=linked_base, control=control)
        if machine is not None:
            v.machine = machine
        control.segment_viewer = v
        if uuid:
            v.uuid = uuid
        control.uuid = v.uuid
        v.create_post()
        print("control: %s, parent: %s uuid:%s" % (control.__class__.__name__, parent.__class__.__name__, v.uuid))
        return v

    ##### Cleanup

    def prepare_for_destroy(self):
        self.control.segment_viewer = None
        self.control = None

    ##### Initialization and serialization

    def create_post(self):
        # hook for subclasses to do some extra init
        pass

    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'uuid' in e:
            self.uuid = e['uuid']

        # FIXME: deprecated stuff?
        if 'machine mime' in e:
            mime = e['machine mime']
            if not mime.startswith(self.machine.mime_prefix):
                m = self.machine.find_machine_by_mime(mime)
                if m is not None:
                    self.machine = m
        if 'font' in e or 'font renderer' in e or 'font order' in e:
            if 'font renderer' in e or 'font order' in e:
                self.set_font(e['font'], e.get('font renderer', None), e.get('font order', None))
            else:
                self.set_font(e['font'][0], e['font'][1])

        if 'machine' in e:
            self.machine.restore_extra_from_dict(e['machine'])
        self.from_metadata_dict_post(e)

    def from_metadata_dict_post(self, e):
        # placeholder for subclasses to check for extra metadata
        pass

    def to_metadata_dict(self, mdict, document):
        mdict['name'] = self.name
        mdict['uuid'] = self.uuid
        mdict['linked base'] = self.linked_base.uuid
        mdict['machine'] = {}
        self.machine.serialize_extra_to_dict(mdict['machine'])
        self.to_metadata_dict_post(mdict, document)

    def to_metadata_dict_post(self, mdict, document):
        # placeholder for subclasses to check for extra metadata
        pass

    def set_machine(self, machine):
        self.machine = machine
        self.reconfigure_panes()

    ##### Range operations

    def _get_range_processor(self):  # Trait property getter
        return ranges_to_indexes

    def get_selected_ranges_and_indexes(self):
        return self.control.get_selected_ranges_and_indexes(self.linked_base)

    def get_selected_index_metadata(self, indexes):
        return self.linked_base.get_selected_index_metadata(indexes)

    def restore_selected_index_metadata(self, metastr):
        return self.linked_base.restore_selected_index_metadata(metastr)

    ##### SegmentViewer interface

    def update_caption(self):
        self.control.SetName(self.window_title)

    ##### Trait change handlers

    # Only the refresh event should actually update the screen! All other trait
    # handlers should just change the data model without any screen effects.

    # Most trait change handlers are simply a trampoline to another method.
    # Trait change events aren't easily overridden in subclasses, so this
    # regular method is what subclasses should use for the desired changes. For
    # example, process_ensure_visible is the trait change handler that calls
    # ensure_visible to do the actual work of repositioning the viewer.

    @on_trait_change('linked_base.editor.document.data_model_changed')
    def process_data_model_change(self, evt):
        log.debug("process_data_model_change for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_data_model()

    @on_trait_change('linked_base.editor.document.recalc_event')
    def process_recalc_view(self, evt):
        log.debug("process_recalc_view for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_view()

    @on_trait_change('linked_base.ensure_visible_index')
    def process_ensure_visible(self, flags):
        log.debug("process_ensure_visible for %s using %s; flags=%s" % (self.control, self.linked_base, str(flags)))
        if flags is not Undefined:
            self.ensure_visible(flags)

    def ensure_visible(self, flags):
        self.control.keep_index_on_screen(flags.index_visible)

    @on_trait_change('linked_base.sync_caret_event')
    def sync_caret_event_handler(self, flags):
        log.debug("process_update_caret for %s using %s; flags=%s" % (self.control, self.linked_base, str(flags)))
        if flags is not Undefined:
            if self.control == flags.source_control:
                log.debug("sync_caret_event: skipping %s" % self.control)
            else:
                log.debug("sync_caret_event: syncing %s" % self.control)
                self.sync_caret(flags)

    def sync_caret(self, flags):
        self.control.set_caret_index(self.linked_base.carets.current.index, flags)

    @on_trait_change('machine.font_change_event,machine.bitmap_shape_change_event,machine.bitmap_color_change_event,machine.disassembler_change_event')
    def machine_metadata_changed(self, evt):
        log.debug("machine_metadata_changed: %s evt=%s" % (self, str(evt)))
        if self.linked_base is not None:
            self.update_caption()
            self.linked_base.editor.update_pane_names()

    @property
    def window_title(self):
        return self.pretty_name

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        pass

    def recalc_view(self):
        """Rebuild the entire UI after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    def show_caret(self, control, index, bit):
        log.debug("show_caret: %s, index=%d" % (self.pretty_name, index))
        self.control.set_caret_index(control, index, bit)

    @on_trait_change('linked_base.refresh_event')
    def refresh_view(self, flags):
        """Redraw the UI
        """
        log.debug("process_refresh_view for %s using %s; flags=%s" % (self.control, self.linked_base, str(flags)))
        if flags is not Undefined:
            if flags.skip_source_control_refresh and self.control == flags.source_control:
                log.debug("refresh_event: skipping refresh of %s" % self.control)
            elif self.control in flags.refreshed_as_side_effect:
                log.debug("refresh_event: skipping already refreshed %s" % self.control)
            else:
                log.debug("refresh_event: refreshing %s" % self.control)
                self.control.refresh_view()

    def get_extra_segment_savers(self, segment):
        """Hook to provide additional ways to save the data based on this view
        of the data
        """
        return []

    ##### toolbar

    def update_toolbar(self):
        pass

    ##### view settings

    @property
    def width(self):
        return self.control.bytes_per_row

    def set_width(self, width):
        self.control.bytes_per_row = self.validate_width(width)
        wx.CallAfter(self.control.recalc_view)

    def validate_width(self, width):
        return width

    @property
    def zoom(self):
        return self.control.zoom

    def set_zoom(self, zoom):
        self.control.zoom = zoom
        wx.CallAfter(self.control.recalc_view)

    ##### Selections

    def select_all(self):
        self.control.select_all(self.linked_base)

    def select_none(self):
        self.control.select_none(self.linked_base)

    def select_invert(self):
        self.control.select_invert(self.linked_base)

    def highlight_selected_ranges(self, caret_handler):
        s = self.linked_base.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges(self.linked_base.selected_ranges, selected=True)

    ##### Clipboard & Copy/Paste

    supported_clipboard_data_objects = [
        wx.CustomDataObject("numpy,multiple"),
        wx.CustomDataObject("numpy"),
        wx.CustomDataObject("numpy,columns"),
        wx.TextDataObject(),
        ]

    @property
    def clipboard_data_format(self):
        return "numpy"

    def get_paste_command(self, serialized_data):
        return PasteCommand

    ##### Fonts

    @property
    def current_antic_font(self):
        if self.antic_font is None:
            self.set_font()
        return self.antic_font

    def get_antic_font(self, reverse=False):
        return fonts.AnticFont(self, self.machine.antic_font_data, self.machine.font_renderer, self.machine.antic_color_registers[4:9], reverse)

    def set_font(self, font=None, font_renderer=None, font_mapping=None):
        if font is None:
            font = self.machine.antic_font_data
        if font_renderer is not None:
            if isinstance(font_renderer, str):
                font_renderer = self.machine.get_font_renderer_from_font_name(font_renderer)
            self.machine.font_renderer = font_renderer
        self.machine.antic_font_data = font
        self.antic_font = self.get_antic_font()
        if self.antic_font.use_blinking:
            self.blinking_antic_font = self.get_antic_font(True)
        else:
            self.blinking_antic_font = None
        self.machine.set_font_mapping(font_mapping)

    def change_font_data(self, data):
        font = dict(data=data[:], blink=self.antic_font.use_blinking)
        self.machine.antic_font_data = font
        self.antic_font = self.get_antic_font()
        if self.antic_font.use_blinking:
            self.blinking_antic_font = self.get_antic_font(True)
        else:
            self.blinking_antic_font = None
        self.machine.set_font_mapping()

    def get_blinking_font(self, index):
        if self.antic_font.use_blinking and index == 1 and self.blinking_antic_font is not None:
            return self.blinking_antic_font
        else:
            return self.antic_font

    ##### Spring tab (pull out menu) interface

    def __call__(self, parent, task, **kwargs):
        control = self.create(parent, task.active_editor.focused_viewer.linked_base)
        return control

    def activate_spring_tab(self):
        self.recalc_view()

    #### popup menus

    def popup_context_menu_from_actions(self, *args, **kwargs):
        self.editor.popup_context_menu_from_actions(self.control, *args, **kwargs)



class ByteViewersPlugin(FrameworkPlugin):
    """ Plugin containing all the viewers for byte data
    """

    # Extension point IDs.
    VIEWERS = 'omnivore8bit.viewers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore8bit.viewer.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'Omnivore Byte Viewers'

    #### Contributions to extension points made by this plugin ################

    viewers = List(contributes_to=VIEWERS)

    segment_viewers = ExtensionPoint(
        List(Instance(SegmentViewer)), id="omnivore8bit.viewers", desc="A list of SegmentViewers that can display the data in a segment"
    )

    def _viewers_default(self):
        from omnivore8bit.viewers.bitmap import MemoryMapViewer
        from omnivore8bit.viewers.bitmap2 import BitmapViewer
        from omnivore8bit.viewers.char2 import CharViewer
        from omnivore8bit.viewers.cpu2 import DisassemblyViewer
        from omnivore8bit.viewers.hex2 import HexEditViewer
        from omnivore8bit.viewers.info import CommentsViewer, UndoViewer, SegmentListViewer
        from omnivore8bit.viewers.map import MapViewer
        from omnivore8bit.viewers.tile import TileViewer
        from omnivore8bit.viewers.jumpman import JumpmanViewer

        return [BitmapViewer, CharViewer, DisassemblyViewer, HexEditViewer, MemoryMapViewer, CommentsViewer, UndoViewer, SegmentListViewer, MapViewer, TileViewer, JumpmanViewer]

plugins = [ByteViewersPlugin()]
