import uuid

import wx

from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined
from envisage.api import ExtensionPoint

from omnivore.framework.plugin import FrameworkPlugin
from ..byte_edit.linked_base import LinkedBase
import omnivore.framework.actions as fa
from ..byte_edit import actions as ba
from ..clipboard_commands import PasteCommand
from ..arch import fonts

from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges
from omnivore.utils.command import DisplayFlags

from omnivore8bit.arch.machine import Machine, Atari800
from omnivore8bit.utils import searchutil
from omnivore8bit.ui.segment_grid import SegmentGridControl
from .mouse_modes import NormalSelectMode
from . import actions as va

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

    viewer_category = "Data"

    control_cls = SegmentGridControl  # override in subclass

    has_editable_bytes = True  # directly user-editable bytes

    has_bitmap = False

    has_font = False  # uses the bitmapped font to display characters

    has_colors = False  # uses machine colors to display stuff

    has_cpu = False

    has_hex = False

    has_text_font = False  # uses the app-wide text font

    has_width = False  # has a user-specifiable items_per_row

    width_text = "viewer width in bytes"

    has_zoom = False  # has user-specifiable zoom value

    zoom_text = "viewer zoom factor"

    has_caret = True

    valid_mouse_modes = []  # toolbar description

    default_mouse_mode_cls = NormalSelectMode

    copy_special = [va.CopyAsReprAction, va.CopyAsCBytesAction]  # additional copy functions available when viewer is present

    paste_special = [ba.PasteCommentsAction]  # additional paste functions available when viewer is present

    searchers = [  # BaseSearcher classes that are applicable to this viewer
        searchutil.HexSearcher,
        searchutil.CommentSearcher,
    ]

    ##### Traits

    uuid = Str

    linked_base = Instance(LinkedBase)

    machine = Instance(Machine)

    control = Any(None)

    range_processor = Property(Any, depends_on='control')

    supported_clipboard_data_objects = List

    antic_font = Any(transient=True)

    blinking_antic_font = Any(transient=True)

    is_tracing = Bool(False)

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
    def document(self):
        return self.linked_base.editor.document

    @property
    def task(self):
        return self.linked_base.task

    @property
    def preferences(self):
        return self.linked_base.cached_preferences

    ##### Class methods

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        # if a control isn't based on SegmentGridControl, this is the place for
        # the subclass to return the custom control
        return cls.control_cls(parent, linked_base, mdict, cls)

    @classmethod
    def check_name(cls, name):
        return name == cls.name

    @classmethod
    def create(cls, parent, linked_base, machine=None, uuid=None, mdict={}):
        control = cls.create_control(parent, linked_base, mdict.get('control',{}))
        v = cls(linked_base=linked_base, control=control)
        v.from_metadata_dict(mdict)
        if machine is not None:
            v.machine = machine
        control.segment_viewer = v
        if uuid:
            v.uuid = uuid
        control.uuid = v.uuid
        v.create_post()
        log.debug("create: control=%s, parent=%s uuid=%s" % (control.__class__.__name__, parent.__class__.__name__, v.uuid))
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
        # 'control' is handled during viewer creation process
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
        mdict['control'] = {}
        try:
            self.control.serialize_extra_to_dict(mdict['control'])
        except AttributeError:
            pass
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
        self.control.SetLabel(self.pretty_name)

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
            log.debug("sync_caret_event: syncing %s" % self.control)
            self.sync_caret(flags)

    def sync_caret(self, flags):
        log.debug("sync_caret: syncing %s" % self.pretty_name)
        if self.has_caret:
            self.control.set_caret_index(self.linked_base.carets.current.index, flags)
        else:
            flags.refreshed_as_side_effect.add(self.control)

    def sync_caret_to_index(self, index, refresh=True):
        log.debug("sync_caret_to_index: syncing %s" % self.pretty_name)
        self.linked_base.carets.force_single_caret(index)
        flags = self.create_mouse_event_flags()
        self.linked_base.sync_caret_event = flags
        if refresh:
            self.linked_base.refresh_event = flags

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
    def process_refresh_view(self, flags):
        """Redraw the UI.

        flags is either True for an unconditional refresh, or a DisplayFlags
        instance that contains more info about what or how to refresh
        """
        log.debug("process_refresh_view for %s using %s; flags=%s" % (self.control, self.linked_base, str(flags)))
        if flags is not Undefined:
            self.refresh_view(flags)

    def refresh_view(self, flags):
        if flags == True:
            log.debug("refresh_event: forcing refresh of %s because no display flags" % self.control)
            self.control.refresh_view()
        elif flags.skip_source_control_refresh and self.control == flags.source_control:
            log.debug("refresh_event: skipping refresh of %s" % self.control)
            # FIXME: the row/col headers aren't refreshed with the call to
            # move_viewport_origin, so force them to be refreshed here. I
            # could just take out the optimization and not skip the source
            # control refresh, but this is not that unpleasant of a hack to
            # save a full refresh of the main grid.
            self.control.refresh_headers()
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
        self.update_mouse_mode()

    def update_mouse_mode(self, mouse_mode=None):
        self.control.set_mouse_mode(mouse_mode)
        self.control.refresh_view()

    ##### view settings

    def use_default_view_params(self):
        self.control.use_default_view_params()

    def restore_view_params(self, params):
        self.control.restore_view_params(params)

    @property
    def width(self):
        return self.control.items_per_row

    def set_width(self, width):
        self.control.items_per_row = self.validate_width(width)
        wx.CallAfter(self.control.recalc_view)

    def validate_width(self, width):
        return width

    @property
    def zoom(self):
        return self.control.zoom

    def set_zoom(self, zoom):
        self.control.zoom = zoom
        wx.CallAfter(self.control.recalc_view)

    ##### Caret

    def create_mouse_event_flags(self):
        flags = DisplayFlags(self.control)
        flags.selecting_rows = False
        flags.old_carets = self.linked_base.carets.get_state()
        return flags

    ##### Selections

    def select_all(self):
        self.control.select_all(self.linked_base)

    def select_none(self):
        self.control.select_none(self.linked_base)

    def select_invert(self):
        self.control.select_invert(self.linked_base)

    def highlight_selected_ranges_in_segment(self, selected_ranges, segment):
        # This is default implementation which simply highlights everything
        # between the start/end values of each range. Other selection types
        # (rectangular selection) will need to be defined in the subclass
        segment.set_style_ranges(selected_ranges, selected=True)

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

    @classmethod
    def all_known_copy_special_actions(cls, task):
        actions = set()
        for v in task.known_viewers:
            actions.update(v.copy_special)
        actions = sorted(actions, key=lambda a:a().name)  # name is a trait, so only exists on an instance, not the class
        return actions

    @classmethod
    def all_known_paste_special_actions(cls, task):
        actions = set()
        for v in task.known_viewers:
            actions.update(v.paste_special)
        actions = sorted(actions, key=lambda a:a().name)  # name is a trait, so only exists on an instance, not the class
        return actions

    ##### Status info and text utilities

    def get_selected_status_message(self):
        carets = self.linked_base.carets_with_selection
        if len(carets) == 0:
            return ""
        if len(carets) == 1:
            c = carets[0]
            num = c.num_selected
            if num == 1: # python style, 4:5 indicates a single byte
                return "[1 byte selected %s]" % self.get_label_of_selections(carets)
            elif num > 0:
                return "[%d bytes selected %s]" % (num, self.get_label_of_selections(carets))
        else:
            return "[%d ranges selected]" % (len(carets))

    def show_status_message(self, msg):
        s = self.get_selected_status_message()
        if s:
            msg = "%s %s" % (msg, s)
        self.task.status_bar.message = msg

    def get_label_at_index(self, index):
        return self.segment.label(index)

    def get_label_of_selections(self, carets):
        labels = []
        for start, end in [c.range for c in carets]:
            labels.append("%s-%s" % (self.get_label_at_index(start), self.get_label_at_index(end - 1)))
        return ", ".join(labels)

    def get_label_of_first_byte(self, carets):
        labels = []
        for start, end in [c.range for c in carets]:
            labels.append(self.get_label_at_index(start))
        return ", ".join(labels)

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

    def calc_viewer_popup_actions(self, popup_data):
        # for subclasses!
        return [va.ViewerWidthAction, va.ViewerZoomAction]

    def popup_context_menu_from_actions(self, *args, **kwargs):
        self.editor.popup_context_menu_from_actions(self.control, *args, **kwargs)


class PlaceholderControl(wx.Window):
    tile_manager_empty_control = True

    def __init__(self, parent, linked_base, mdict, viewer_cls):
        wx.Window.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.draw(dc)

    def draw(self, dc):
        size = self.GetClientSize()
        s = "Size: %d x %d"%(size.x, size.y)
        dc.SetFont(wx.NORMAL_FONT)
        w, height = dc.GetTextExtent(s)
        height += 3
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)
        dc.DrawText(s, (size.x-w)/2, (size.y-height*5)/2)
        pos = self.GetPosition()
        s = "Position: %d, %d" % (pos.x, pos.y)
        w, h = dc.GetTextExtent(s)
        dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*3))

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        size = self.GetClientSize()
        s = "Size: %d x %d"%(size.x, size.y)
        self.SetName(s)
        self.Refresh()

    def recalc_view(self):
        self.refresh_view()

    def refresh_view(self):
        dc = wx.ClientDC(self)
        self.draw(dc)

    def refresh_headers(self):
        pass


class PlaceholderViewer(SegmentViewer):
    name = "placeholder"

    pretty_name = "Placeholder"

    control_cls = PlaceholderControl

    has_editable_bytes = False


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
        # from omnivore8bit.viewers.bitmap import MemoryMapViewer
        from omnivore8bit.viewers.bitmap2 import BitmapViewer
        from omnivore8bit.viewers.char2 import CharViewer
        from omnivore8bit.viewers.cpu2 import DisassemblyViewer
        from omnivore8bit.viewers.hex2 import HexEditViewer
        from omnivore8bit.viewers.info import CommentsViewer, UndoViewer, SegmentListViewer
        from omnivore8bit.viewers.map2 import MapViewer
        from omnivore8bit.viewers.tile import TileViewer
        from omnivore8bit.viewers.jumpman2 import JumpmanViewer, TriggerPaintingViewer, LevelSummaryViewer
        from omnivore8bit.viewers.emulator import Atari800Viewer, CPU6502Viewer

        return [BitmapViewer, CharViewer, DisassemblyViewer, HexEditViewer, CommentsViewer, UndoViewer, SegmentListViewer, MapViewer, TileViewer, JumpmanViewer, TriggerPaintingViewer, LevelSummaryViewer, Atari800Viewer, CPU6502Viewer]

plugins = [ByteViewersPlugin()]
