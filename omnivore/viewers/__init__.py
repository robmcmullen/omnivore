import uuid
import random

import wx

from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined
from envisage.api import ExtensionPoint

from omnivore_framework.framework.plugin import FrameworkPlugin
from ..byte_edit.linked_base import LinkedBase
import omnivore_framework.framework.actions as fa
from ..byte_edit import actions as ba
from ..clipboard_commands import PasteCommand
from ..arch import fonts

from omnivore_framework.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges
from omnivore_framework.utils.command import DisplayFlags

from ..arch.machine import Machine, Atari800
from ..utils import searchutil
from ..ui.segment_grid import SegmentGridControl
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

    override_table_cls = None  # override grid table

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

    frame_count = Int

    priority_refresh_frame_count = Int(10)

    #### Default traits

    def _uuid_default(self):
        return str(uuid.uuid4())

    def _machine_default(self):
        return None

    def _supported_clipboard_data_objects_default(self):
        return [a[0] for a in self.supported_clipboard_data_object_map.values()]

    def _frame_count_default(self):
        # start the initial frame count on a random value so the frame refresh
        # load can be spread around instead of each with the same frame count
        # being refreshed at the same time.
        return random.randint(0, self.priority_refresh_frame_count)

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
    def is_segment_specific_for_display(cls, segment):
        return False

    @classmethod
    def calc_segment_specific_linked_base(cls, editor):
        # Some viewers need a particular address range to display correctly,
        # e.g. the Apple 2 hires and text modes. If one is needed, create and
        # return it here.
        for s in editor.document.segments:
            if cls.is_segment_specific_for_display(s):
                linked_base = LinkedBase(editor=editor)
                linked_base.find_segment(s, data_model_changed=False)
                break
        else:
            linked_base = None
        return linked_base

    @classmethod
    def replace_linked_base(cls, linked_base):
        """If the subclass uses a cursor and the cursor isn't indexed the same
        as the default linked_base, this is the opportunity to replace it with
        a different linked base that will disassociate the cursors. This means
        this subclass will not share selection or cursor movement.
        """
        return linked_base

    @classmethod
    def viewer_factory(cls, parent, linked_base, machine=None, uuid=None, mdict={}):
        linked_base = cls.replace_linked_base(linked_base)
        control = cls.create_control(parent, linked_base, mdict.get('control',{}))
        v = cls(linked_base=linked_base, control=control)
        if machine is not None:
            v.machine = machine
        v.from_metadata_dict(mdict)

        if v.machine is None:
            print("LOOKING UP MACHINE BY MIME", linked_base.document.metadata.mime)
            v.machine = Machine.find_machine_by_mime(linked_base.document.metadata.mime, default_if_not_matched=True)

        control.segment_viewer = v
        if uuid:
            v.uuid = uuid
        control.uuid = v.uuid
        try:
            control.verify_line_renderer()
        except AttributeError:
            pass
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
        if 'machine' in e:
            if self.machine is None:
                self.machine = Machine()
            self.machine.restore_extra_from_dict(e['machine'])
        elif 'machine mime' in e:
            mime = e['machine mime']
            if self.machine is None or not mime.startswith(self.machine.mime_prefix):
                m = Machine.find_machine_by_mime(mime)
                if m is not None:
                    self.machine = m

        if 'font' in e or 'font renderer' in e or 'font order' in e:
            if 'font renderer' in e or 'font order' in e:
                self.set_font(e['font'], e.get('font renderer', None), e.get('font order', None))
            else:
                self.set_font(e['font'][0], e['font'][1])

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

    ##### User interface

    def is_toggle_set(self, toggle_flag):
        return self.linked_base == self.editor.center_base

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
        self.control.SetName(self.window_title + self.linked_base_segment_identifier)
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

    @property
    def linked_base_segment_identifier(self):
        """If the viewer is always associated with a particular segment
        override this to return an empty string
        """
        return f" ({self.linked_base.segment.name})"

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

    @on_trait_change('linked_base.editor.document.priority_level_refresh_event')
    def process_priority_level_refresh(self, evt):
        """Refresh based on frame count and priority. If the value passed
        through this event is an integer, all viewers with priority values less
        than the event priority value (i.e. the viewers with a higher priority)
        will be refreshed.
        """
        log.debug("process_priority_level_refresh for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.frame_count += 1
            p = self.priority_refresh_frame_count
            if self.frame_count > p or p < evt:
                self.do_priority_level_refresh()
                self.frame_count = 0

    def do_priority_level_refresh(self):
        self.refresh_view(True)

    @on_trait_change('linked_base.editor.document.emulator_breakpoint_event')
    def process_emulator_breakpoint(self, evt):
        log.debug("process_emulator_breakpoint for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.do_emulator_breakpoint()

    def do_emulator_breakpoint(self):
            self.task.status_bar.message = f"{self.document.emulator.cycles_since_power_on} cycles"

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
    VIEWERS = 'omnivore.viewers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore.viewer.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'Omnivore Byte Viewers'

    #### Contributions to extension points made by this plugin ################

    viewers = List(contributes_to=VIEWERS)

    segment_viewers = ExtensionPoint(
        List(Instance(SegmentViewer)), id="omnivore.viewers", desc="A list of SegmentViewers that can display the data in a segment"
    )

    def _viewers_default(self):
        # from ..viewers.bitmap import MemoryMapViewer
        from ..viewers.bitmap2 import BitmapViewer
        from ..viewers.char2 import CharViewer
        # from ..viewers.cpu2 import DisassemblyViewer as OldDisassemblyViewer
        from ..viewers.hex2 import HexEditViewer
        from ..viewers.info import CommentsViewer, UndoViewer, SegmentListViewer
        from ..viewers.map2 import MapViewer
        # from ..viewers.tile import TileViewer
        from ..viewers.jumpman2 import JumpmanViewer, TriggerPaintingViewer, LevelSummaryViewer
        from ..viewers.emulator import VideoViewer, CPU6502Viewer, ANTICViewer, POKEYViewer, GTIAViewer, PIAViewer
        from ..viewers.apple2 import HiresPage1Viewer, HiresPage2Viewer, TextPage1Viewer, TextPage2Viewer
        from ..viewers.memory import MemoryAccessViewer
        from ..viewers.skeleton import VirtualTestViewer
        from ..viewers.disasm import DisassemblyViewer
        from ..viewers.history import InstructionHistoryViewer

        return [BitmapViewer, CharViewer, DisassemblyViewer, HexEditViewer, CommentsViewer, UndoViewer, SegmentListViewer, MapViewer, JumpmanViewer, TriggerPaintingViewer, LevelSummaryViewer, VideoViewer, CPU6502Viewer, ANTICViewer, POKEYViewer, GTIAViewer, PIAViewer, HiresPage1Viewer, HiresPage2Viewer, TextPage1Viewer, TextPage2Viewer, MemoryAccessViewer, VirtualTestViewer, InstructionHistoryViewer]

plugins = [ByteViewersPlugin()]
