import uuid
import random
import inspect
import pkg_resources

import wx

from .editors.linked_base import LinkedBase
from .arch import fonts

from sawx import errors
from sawx.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges

from .utils import searchutil
from .ui.segment_grid import SegmentGridControl
from .viewers.mouse_modes import NormalSelectMode
# from . import actions as va

import logging
log = logging.getLogger(__name__)
caret_log = logging.getLogger("caret")
# caret_log.setLevel(logging.DEBUG)


known_viewers = {}

def get_viewers():
    global known_viewers

    if not known_viewers:
        viewers = {}
        for entry_point in pkg_resources.iter_entry_points('omnivore.viewers'):
            mod = entry_point.load()
            log.debug(f"get_viewers: Found module {entry_point.name}")
            for name, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and SegmentViewer in obj.__mro__ and obj.name:
                    log.debug(f"get_viewers: Found viewer class {name}")
                    viewers[obj.name] = obj
        known_viewers = viewers
    return known_viewers


def find_viewer_class_by_name(name):
    """Find the editor class given its class name

    Returns the OmnivoreEditor subclass whose `name` class attribute matches
    the given string.
    """
    viewers = get_viewers()
    log.debug(f"finding viewers using {viewers}")
    try:
        return viewers[name]
    except KeyError:
        raise errors.EditorNotFound(f"No viewer named {name}")


class SegmentViewer:
    """Base class for any viewer window that can display (& optionally edit)
    the data in a segment

    Linked base exists for the lifetime of the viewer. If the user wants to
    change the base, a new viewer is created and replaces this viewer.
    """
    ##### class attributes

    name = ""  # slug to uniquely identify viewer class

    ui_name = ""  # text to be used in titles and menus

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

    popup_menu_desc = [
        "view_width",
        "view_zoom",
        None,
        "copy"
        "cut",
        "paste",
        None,
        ["Copy Special",
            "copy_as_repr",
            "copy_as_c_bytes",
            "copy_disassembly",
            "copy_disassembly_comments",
        ],
        ["Paste Special",
            "paste_comments",
            "paste_disassembly_comments",
        ],
        None,
        "select_all",
        "select_none",
        None,
        ["Mark Selection As",
            "disasm_type",
        ],
        None,
        "segment_from_selection",
        "segment_revert_to_baseline",
        None,
        "segment_add_comment",
        "segment_remove_comment",
        "segment_add_label",
        "segment_remove_label",
    ]

    searchers = [  # BaseSearcher classes that are applicable to this viewer
        searchutil.HexSearcher,
        searchutil.CommentSearcher,
    ]

    priority_refresh_frame_count = 10

    # List of menu bar titles to be excluded from the menu bar when this viewer
    # is focused
    exclude_from_menubar = ["Jumpman"]

    # List of toolbar items that should only be shown with this viewer
    viewer_extra_toolbar_desc = []

    def __init__(self, control, linked_base):
        self.uuid = str(uuid.uuid4())
        self.control = control
        self.linked_base = linked_base

        self.range_processor = ranges_to_indexes
        self.is_tracing = False

        # start the initial frame count on a random value so the frame refresh
        # load can be spread around instead of each with the same frame count
        # being refreshed at the same time.
        self.frame_count = random.randint(0, self.priority_refresh_frame_count)

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
    def frame(self):
        return self.linked_base.editor.frame

    @property
    def preferences(self):
        return self.linked_base.editor.preferences

    @property
    def is_focused_viewer(self):
        return self.linked_base.editor.focused_viewer == self

    @property
    def can_copy(self):
        if self.has_caret:
            return self.control.caret_handler.has_selection
        return False

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
    def viewer_factory(cls, parent, linked_base, uuid=None, mdict={}):
        linked_base = cls.replace_linked_base(linked_base)
        control = cls.create_control(parent, linked_base, mdict.get('control',{}))
        print("LINKEDBASE:", linked_base.__class__.__mro__)
        v = cls(control, linked_base)
        v.restore_session(mdict)

        # if v.machine is None:
        #     print("LOOKING UP MACHINE BY MIME", linked_base.document.mime)
        #     v.machine = Machine.find_machine_by_mime(linked_base.document.mime, default_if_not_matched=True)

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
        v.set_event_handlers()
        return v

    @classmethod
    def get_known_subclasses(cls):
        return get_all_subclasses_of(SegmentViewer)

    ##### Cleanup

    def prepare_for_destroy(self):
        self.control.segment_viewer = None
        self.control = None

    ##### Initialization and serialization

    def create_post(self):
        # hook for subclasses to do some extra init
        pass

    def set_event_handlers(self):
        self.document.byte_values_changed_event += self.on_refresh_view_for_value_change
        self.document.byte_style_changed_event += self.on_refresh_view_for_style_change
        self.document.structure_changed_event += self.on_recalc_data_model
        self.document.recalc_event += self.on_recalc_view
        self.document.priority_level_refresh_event += self.on_priority_level_refresh
        self.document.emulator_breakpoint_event += self.on_emulator_breakpoint
        self.linked_base.ensure_visible_event += self.on_ensure_visible
        self.linked_base.sync_caret_to_index_event += self.on_sync_caret_to_index
        self.linked_base.refresh_event += self.on_refresh_view
        self.linked_base.recalc_event += self.on_recalc_view

    def restore_session(self, s):
        log.debug("restore_session: %s" % str(s))
        if 'uuid' in s:
            self.uuid = s['uuid']

        # FIXME: deprecated stuff?
        # if 'machine' in e:
        #     if self.machine is None:
        #         self.machine = Machine()
        #     self.machine.restore_extra_from_dict(e['machine'])
        # elif 'machine mime' in e:
        #     mime = e['machine mime']
        #     if self.machine is None or not mime.startswith(self.machine.mime_prefix):
        #         m = Machine.find_machine_by_mime(mime)
        #         if m is not None:
        #             self.machine = m

        # if 'font' in e or 'font renderer' in e or 'font order' in e:
        #     if 'font renderer' in e or 'font order' in e:
        #         self.set_font(e['font'], e.get('font renderer', None), e.get('font order', None))
        #     else:
        #         self.set_font(e['font'][0], e['font'][1])

        # 'control' is handled during viewer creation process

    def serialize_session(self, s):
        s['name'] = self.name
        s['uuid'] = self.uuid
        s['linked base'] = self.linked_base.uuid
        s['control'] = {}
        try:
            self.control.serialize_extra_to_dict(s['control'])
        except AttributeError:
            pass

    ##### User interface

    def is_toggle_set(self, toggle_flag):
        return self.linked_base == self.editor.center_base

    ##### Range operations

    def get_selected_ranges_and_indexes(self):
        return self.control.get_selected_ranges_and_indexes(self.linked_base)

    def get_selected_index_metadata(self, indexes):
        return self.linked_base.get_selected_index_metadata(indexes)

    def restore_selected_index_metadata(self, metastr):
        return self.linked_base.restore_selected_index_metadata(metastr)

    ##### SegmentViewer interface

    def update_caption(self):
        self.control.SetName(self.window_title + self.linked_base_segment_identifier)
        self.control.SetLabel(self.ui_name)

    ##### non-wx event handlers

    # Only the refresh event should actually update the screen! All other event
    # handlers should just change the data model without any screen effects.

    def on_ensure_visible(self, evt):
        flags = evt.flags
        if flags.index_visible is not None:
            self.control.keep_index_on_screen(flags.index_visible, flags)

    def on_sync_caret_to_index(self, evt):
        flags = evt.flags
        caret_log.debug("sync_caret_to_index_event: for %s using %s; flags=%s" % (self.control, self.linked_base, str(flags)))
        if self.control == flags.source_control or self.control == flags.advance_caret_position_in_control:
            caret_log.debug(f"sync_caret_to_index_event: skipping {self.control} because is the source of the carets")
        else:
            caret_log.debug("sync_caret_to_index_event: syncing %s" % self.control)
            self.sync_caret(flags)

    def sync_caret(self, flags):
        if self.has_caret:
            if flags.carets_to_indexes:
                caret_log.debug(f"sync_caret: {self.ui_name} has carets; syncing from {flags.carets_to_indexes}")
                self.control.caret_handler.convert_from_indexes(self.control.table, flags.carets_to_indexes)
                self.control.keep_current_caret_on_screen(flags)
            else:
                caret_log.debug(f"sync_caret: caret position/selection unchanged")
        else:
            caret_log.debug(f"sync_caret: {self.ui_name} refreshed as side effect")
            flags.refreshed_as_side_effect.add(self.control)

    @property
    def window_title(self):
        return self.ui_name

    @property
    def linked_base_segment_identifier(self):
        """If the viewer is always associated with a particular segment
        override this to return an empty string
        """
        return f" ({self.linked_base.segment.name})"

    def on_recalc_data_model(self, evt):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        self.recalc_data_model()

    def recalc_data_model(self):
        pass

    def on_recalc_view(self, evt):
        self.recalc_view()

    def recalc_view(self):
        """Rebuild the entire UI after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    def show_caret(self, control, index, bit):
        caret_log.debug("show_caret: %s, index=%d" % (self.ui_name, index))
        self.control.set_caret_index(control, index, bit)

    def on_priority_level_refresh(self, evt):
        """Refresh based on frame count and priority. If the value passed
        through this event is an integer, all viewers with priority values less
        than the event priority value (i.e. the viewers with a higher priority)
        will be refreshed.
        """
        log.debug("process_priority_level_refresh for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        self.frame_count += 1
        p = self.priority_refresh_frame_count
        if self.frame_count > p or p < evt:
            self.do_priority_level_refresh()
            self.frame_count = 0

    def do_priority_level_refresh(self):
        self.refresh_view(True)

    def on_emulator_breakpoint(self, evt):
        log.debug("process_emulator_breakpoint for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        self.do_emulator_breakpoint()

    def do_emulator_breakpoint(self, evt):
            self.frame.status_message(f"{self.document.emulator.cycles_since_power_on} cycles")

    def on_refresh_view(self, evt):
        self.refresh_view(evt.flags)

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

    def on_refresh_view_for_value_change(self, evt):
        self.refresh_view(evt.flags)

    def on_refresh_view_for_style_change(self, evt):
        self.refresh_view(evt.flags)

    def get_extra_segment_savers(self, segment):
        """Hook to provide additional ways to save the data based on this view
        of the data
        """
        return []

    ##### toolbar

    def prune_menubar(self, orig_desc):
        desc = []
        for menu in orig_desc:
            if self.is_menu_valid(menu[0]):
                desc.append(menu)
        return desc

    def is_menu_valid(self, menu):
        return menu not in self.exclude_from_menubar

    def prune_toolbar(self, orig_desc):
        desc = []
        for tool in orig_desc:
            if tool is None or self.is_tool_valid(tool):
                desc.append(tool)
        if self.viewer_extra_toolbar_desc:
            if desc:
                desc.append(None)
            desc.extend(self.viewer_extra_toolbar_desc)
        return desc

    def is_tool_valid(self, menu):
        return True

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

    ##### Selections

    def select_all(self):
        self.control.mouse_mode.select_all(self.control.caret_handler)

    def select_none(self):
        self.control.mouse_mode.select_none(self.control.caret_handler)

    def select_invert(self):
        self.control.mouse_mode.select_invert(self.control.caret_handler)

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

    def get_paste_command(self, serialized_data, *args, **kwargs):
        return PasteCommand(self.segment, serialized_data, *args, **kwargs)

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
        self.frame.status_message(msg)

    def get_label_at_index(self, index):
        return self.segment.label(index)

    def get_label_of_selections(self, carets):
        labels = []
        for start, end in [c.range for c in carets]:
            labels.append("%s-%s" % (self.get_label_at_index(start), self.get_label_at_index(end - 1)))
        return ", ".join(labels)

    def get_label_of_first_byte(self, ranges):
        labels = []
        for start, end in ranges:
            labels.append(self.get_label_at_index(start))
        return ", ".join(labels)

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

    ui_name = "Placeholder"

    control_cls = PlaceholderControl

    has_editable_bytes = False
