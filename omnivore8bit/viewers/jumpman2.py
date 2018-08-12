import os
import sys

import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, selected_bit_mask, comment_bit_mask, user_bit_mask, match_bit_mask

from traits.api import on_trait_change, Bool, Undefined, Int, Str, Dict, Any

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg
from omnivore.templates import get_template

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from ..ui.info_panels import InfoPanel
from ..arch.machine import Machine
from ..arch.antic_renderers import BaseRenderer
from ..arch.colors import powerup_colors
from ..jumpman import parser as ju
from ..jumpman import playfield as jp
from ..jumpman import savers as js

from . import SegmentViewer
from . import actions as va
from ..jumpman import mouse_modes as jm
from ..jumpman import commands as jc
from .bitmap2 import BitmapGridControl, BitmapViewer, BitmapLineRenderer
from .info import BaseInfoViewer

import logging
log = logging.getLogger(__name__)
drawlog = logging.getLogger("refresh")


class JumpmanPlayfieldRenderer(BaseRenderer):
    """ Custom renderer instead of Antic Mode D renderer. Need to display
    highlighting on a per-pixel level which isn't possible with the Mode D
    renderer because the styling info is applied at the byte level and there
    are 4 pixels per byte in Mode D.

    So this renderer is one byte per pixel, but only uses the first 16 colors.
    It is mapped to the ANTIC color register order, so the first 4 colors are
    player colors, then the 5 playfield colors. A blank screen corresponds to
    the index value of 8, so the last playfield color.
    """
    name = "Jumpman 1 Byte Per Pixel"
    pixels_per_byte = 1
    bitplanes = 1

    def get_image(self, segment_viewer, bytes_per_row, nr, count, pixels, style):
        normal = style == 0
        highlight = (style & selected_bit_mask) == selected_bit_mask
        comment = (style & comment_bit_mask) == comment_bit_mask
        data = (style & user_bit_mask) > 0
        match = (style & match_bit_mask) == match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = self.get_colors(segment_viewer, list(range(32)))
        bitimage = np.empty((nr * bytes_per_row, 3), dtype=np.uint8)
        for i in range(32):
            color_is_set = (pixels == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:] = segment_viewer.preferences.empty_background_color[0:3]
        return bitimage.reshape((nr, bytes_per_row, 3))


class JumpmanFrameRenderer(BitmapLineRenderer):
    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        model = grid_control.model
        first_col = self.cell_to_col[first_cell]
        last_cell = min(first_cell + visible_cells, self.num_cells)
        last_col = self.cell_to_col[last_cell - 1] + 1
        last_row = min(first_row + visible_rows, model.antic_lines)
        drawlog.debug("draw_grid: rows:%d,%d, cols:%d,%d" % (first_row, last_row, first_col, last_col))

        ul_rect = self.col_to_rect(first_row, first_col)
        lr_rect = self.col_to_rect(last_row - 1, last_col - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)

        bytes_per_row = model.items_per_row
        first_index = first_row * bytes_per_row
        last_index = last_row * bytes_per_row
        data = model.data[first_index:last_index]
        style = model.style[first_index:last_index]
        drawlog.debug("draw_grid: first_index:%d last_index:%d" % (first_index, last_index))

        array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, bytes_per_row, last_row - first_row, last_index - first_index, data, style)
        width = array.shape[1]
        height = array.shape[0]
        drawlog.debug("Calculated image: %dx%d" % (width, height))
        if width > 0 and height > 0:
            # image returned will have the correct number of rows but will be
            # 160 pixels wide; need to crop to visible columns
            cropped = array[:,first_col:last_col,:]
            array = intscale(cropped, grid_control.zoom_h, grid_control.zoom_w)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tobytes())
            bmp = wx.Bitmap(image)
            dc.SetClippingRegion(frame_rect)
            dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class JumpmanMachine(Machine):

    ##### Trait initializers

    def _name_default(self):
        return "Jumpman"

    def _bitmap_renderer_default(self):
        return JumpmanPlayfieldRenderer()

    def _mime_prefix_default(self):
        return "application/vnd.atari8bit"


class JumpmanSegmentTable(cg.HexTable):
    def __init__(self, linked_base, bytes_per_row):
        self.model = linked_base.jumpman_playfield_model
        cg.HexTable.__init__(self, self.model.playfield, self.model.playfield.style, self.model.items_per_row, 0x7000)

    @property
    def segment(self):
        return self.linked_base.segment

    def get_label_at_index(self, index):
        return (index // 40)


class JumpmanGridControl(BitmapGridControl):
    default_table_cls = JumpmanSegmentTable

    @property
    def model(self):
        return self.table.model

    def set_viewer_defaults(self):
        self.items_per_row = 160
        self.zoom = 4
        self.want_col_header = False
        self.want_row_header = False

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return JumpmanFrameRenderer(self, self.segment_viewer)
        return SegmentGridControl.calc_line_renderer(self)

    def recalc_view_extra_setup(self):
        self.model.init_level_builder(self.segment_viewer)

    def refresh_view(self, *args, **kwargs):
        drawlog.debug("refresh_view")
        self.model.draw_playfield(True)
        BitmapGridControl.refresh_view(self, *args, **kwargs)

    def draw_carets(self, *args, **kwargs):
        pass

    ##### popup stuff

    def get_extra_actions(self):
        return []

    ##### selections

    def select_all(self, caret_handler):
        """ Selects the entire document
        """
        mouse_mode = self.mouse_mode
        if mouse_mode.can_paste:
            first = True
            for obj in self.model.level_builder.objects:
                print(("select_all: adding %s" % str(obj)))
                mouse_mode.add_to_selection(obj, not first)
                first = False
            if not first:
                self.refresh_view()

    def select_none(self, caret_handler):
        """ Clears any selection in the document
        """
        mouse_mode = self.mouse_mode
        if mouse_mode.can_paste:
            mouse_mode.objects = []
            self.refresh_view()

    def select_invert(self, caret_handler):
        """ Selects the entire document
        """
        mouse_mode = self.mouse_mode
        if mouse_mode.can_paste:
            first = True
            current = set(mouse_mode.objects)
            for obj in self.model.level_builder.objects:
                if obj not in current:
                    mouse_mode.add_to_selection(obj, not first)
                    first = False
            if not first:
                self.refresh_view()

    ##### Keyboard handling

    def handle_char_move_backspace(self, evt, flags):
        self.mouse_mode.delete_objects()

    handle_char_move_delete = handle_char_move_backspace


class JumpmanViewer(BitmapViewer):
    name = "jumpman"

    pretty_name = "Jumpman Level Editor"

    control_cls = JumpmanGridControl

    has_bitmap = True

    has_colors = True

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    has_caret = False

    ##### Traits

    can_select_objects = Bool(False)

    can_erase_objects = Bool(False)

    ##### class attributes

    valid_mouse_modes = [jm.AnticDSelectMode, jm.DrawGirderMode, jm.DrawLadderMode, jm.DrawUpRopeMode, jm.DrawDownRopeMode, jm.DrawPeanutMode, jm.EraseGirderMode, jm.EraseLadderMode, jm.EraseRopeMode, jm.JumpmanRespawnMode]

    default_mouse_mode_cls = jm.AnticDSelectMode

    #### Default traits

    def _machine_default(self):
        return JumpmanMachine()

    def _draw_pattern_default(self):
        return [0]

    ##### Properties

    @property
    def window_title(self):
        return "Jumpman Level Editor"

    @property
    def current_level(self):
        return self.linked_base.jumpman_playfield_model

    ##### Initialization and serialization

    def from_metadata_dict_post(self, e):
        # ignore bitmap renderer in restore because we always want to use the
        # JumpmanPlayfieldRenderer in Jumpman level edit mode
        if 'assembly_source' in e:
            self.current_level.assembly_source = e['assembly_source']
        if 'old_trigger_mapping' in e:
            self.current_level.old_trigger_mapping = e['old_trigger_mapping']

    def to_metadata_dict_post(self, mdict, document):
        mdict["assembly_source"] = self.current_level.assembly_source
        mdict["old_trigger_mapping"] = dict(self.current_level.old_trigger_mapping)  # so we don't try to pickle a TraitDictObject

    def get_extra_segment_savers(self, segment):
        """Hook to provide additional ways to save the data based on this view
        of the data
        """
        return [js.JumpmanSaveAsATR, js.JumpmanSaveAsXEX]

    ##### Trait change handlers

    def recalc_data_model(self):
        self.current_level.init_level_builder(self)
        self.machine.update_colors(self.current_level.level_colors)

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    @on_trait_change('linked_base.editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.control.recalc_view()

    @on_trait_change('linked_base.jumpman_trigger_selected_event')
    def do_jumpman_trigger_selected_event(self, new_trigger_root):
        log.debug("jumpman_trigger_selected_changed: %s selected=%s" % (self, str(new_trigger_root)))
        if new_trigger_root is not Undefined:
            self.set_trigger_view(new_trigger_root)

    ##### Jumpman level construction

    def update_harvest_state(self):
        if not self.current_level.valid_level:
            return
        harvest_state = self.current_level.level_builder.get_harvest_state()
        self.num_ladders = len(harvest_state.ladder_positions)
        self.num_downropes = len(harvest_state.downrope_positions)
        self.num_peanuts = len(harvest_state.peanuts)

        # FIXME: force redraw of level data here because it depends on the
        # level builder objects so it can count the number of items
        #self.level_data.refresh_view()
        #self.trigger_list.refresh_view()

    def set_trigger_view(self, trigger_root):
        level = self.current_level
        mouse_mode = level.mouse_mode
        if mouse_mode.can_paste:
            mouse_mode.objects = []
        level.set_trigger_root(trigger_root)
        self.can_erase_objects = trigger_root is not None
        self.control.refresh_view()


##### Trigger painting viewer

class TriggerList(wx.ListBox):
    """Trigger selector for choosing which trigger actions to edit
    """

    def __init__(self, parent, linked_base, mdict, viewer_cls, **kwargs):
        self.triggers = None

        wx.ListBox.__init__(self, parent, style=wx.LB_SINGLE, **kwargs)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LISTBOX, self.on_click)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_MOTION, self.on_tooltip)

    def DoGetBestSize(self):
        """ Base class virtual method for sizer use to get the best size
        """
        width = 300
        height = -1
        best = wx.Size(width, height)

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best

    def recalc_view(self):
        try:
            level = self.segment_viewer.linked_base.jumpman_playfield_model
        except ValueError:
            self.SetItems([])
            self.triggers = [None]
        else:
            self.set_peanuts(level)

    def refresh_view(self):
        if self.IsShown():
            drawlog.debug("refreshing %s" % self)
            self.recalc_view()
        else:
            drawlog.debug("skipping refresh of hidden %s" % self)

    def parse_peanuts(self, peanuts, items, triggers, indent=""):
        for peanut in peanuts:
            items.append(indent + peanut.trigger_str)
            triggers.append(peanut)
            children = []
            for p in peanut.trigger_painting:
                if p.single:
                    children.append(p)
            if children:
                self.parse_peanuts(children, items, triggers, indent + "    ")

    def set_peanuts(self, level):
        items = ["Main Level"]
        triggers = [None]
        index = 1
        selected_index = 0
        state = level.screen_state
        if state is not None:
            self.parse_peanuts(state.sorted_peanuts, items, triggers)
            for index, trigger in enumerate(triggers):
                if trigger == level.trigger_root:
                    selected_index = index
        if len(items) != self.GetCount():
            self.SetItems(items)
        else:
            for i, item in enumerate(items):
                old = self.GetString(i)
                if old != item:
                    self.SetString(i, item)
        if selected_index < self.GetCount():
            self.SetSelection(selected_index)
        self.triggers = triggers

    def on_left_down(self, event):
        item = self.HitTest(event.GetPosition())
        if item >= 0:
            selected = self.GetSelection()
            if selected != item:
                wx.CallAfter(self.update_triggers_in_main_viewer, self.triggers[item])
        event.Skip()

    def on_click(self, event):
        # BUG: doesn't seem to get called when selecting a segment, using the
        # comments sidebar to jump to another segment, then attempting to
        # select that previous segment. This function never gets called in
        # that case, so I had to add the check on EVT_LEFT_DOWN
        is_selected = event.GetExtraLong()
        if is_selected:
            selected = event.GetSelection()
            wx.CallAfter(self.update_triggers_in_main_viewer, self.triggers[selected])
        event.Skip()

    def update_triggers_in_main_viewer(self, new_trigger_root):
        print(("new trigger root:", new_trigger_root))
        self.segment_viewer.linked_base.jumpman_trigger_selected_event = new_trigger_root

    def on_dclick(self, event):
        event.Skip()

    def on_tooltip(self, evt):
        pos = evt.GetPosition()
        selected = self.HitTest(pos)
        if selected >= 0:
            message = "peanut #%d" % selected
        else:
            message = ""
        # FIXME: set message, maybe in title bar?
        evt.Skip()


class TriggerPaintingViewer(BaseInfoViewer):
    name = "trigger_painting"

    pretty_name = "Jumpman Trigger Painting"

    control_cls = TriggerList

    def recalc_data_model(self):
        pass

    def show_caret(self, control, index, bit):
        pass

    @on_trait_change('linked_base.segment_selected_event')
    def process_segment_selected(self, evt):
        log.debug("process_segment_selected for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_view()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0


class JumpmanInfoPanel(InfoPanel):
    fields = [
        ("text", "Level Number", 0x00, 2),
        ("atascii_gr2_0xc0", "Level Name", 0x3ec, 20),
        ("uint", "Points per Peanut", 0x33, 2, 250),
        ("label", "# Peanuts", "num_peanuts", 42),
        ("peanuts_needed", "Peanuts Needed", 0x3e, 1, ["All", "All except 1", "All except 2", "All except 3", "All except 4"]),
        ("uint", "Bonus Value", 0x35, 2, 2500),
        ("dropdown", "Number of Bullets", 0x3d, 1, ["None", "1", "2", "3", "4"]),
        ("antic_colors", "Game Colors", 0x2a, 9),
        ("label", "# Columns with Ladders", "num_ladders", 12),
        ("label", "# Columns with Downropes", "num_downropes", 6),
    ]

    def is_valid_data(self):
        jm = self.linked_base.jumpman_playfield_model
        return jm.possible_jumpman_segment and bool(jm.level_builder.objects)


class LevelSummaryViewer(BaseInfoViewer):
    name = "level_summary"

    pretty_name = "Jumpman Level Summary"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        control = JumpmanInfoPanel(parent, linked_base, size=(350, 150))
        return control

    def recalc_data_model(self):
        pass

    def show_caret(self, control, index, bit):
        pass

    @on_trait_change('linked_base.segment_selected_event')
    def process_segment_selected(self, evt):
        log.debug("process_segment_selected for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_view()

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0



##### Class level utilities

def find_first_valid_segment_index(segments):
    """Find first valid jumpman level in the list of segments.

    This prefers segments that are exactly 0x800 bytes long, but will return
    longer segments that look like they contain level data if no segments of
    the exact length are found.
    """
    possible = []
    for i, segment in enumerate(segments):
        if ju.is_valid_level_segment(segment):
            possible.append(i)
            if len(segment) == 0x800:
                return i
    if possible:
        return possible[0]
    return 0
