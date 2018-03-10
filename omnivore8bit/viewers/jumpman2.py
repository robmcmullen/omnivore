import os
import sys

import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, selected_bit_mask, comment_bit_mask, user_bit_mask, match_bit_mask

from traits.api import on_trait_change, Bool, Undefined, Int, Str, Dict, Any

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from ..arch.machine import Machine
from ..arch.antic_renderers import BaseRenderer
from ..arch.colors import powerup_colors
from ..utils import jumpman as ju

from . import SegmentViewer
from . import actions as va
from . import jumpman_mouse_modes as jm
from . import jumpman_commands as jc
from .bitmap2 import BitmapGridControl, BitmapViewer

import logging
log = logging.getLogger(__name__)


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

    def get_image(self, segment_viewer, bytes_per_row, nr, count, bytes, style):
        normal = style == 0
        highlight = (style & selected_bit_mask) == selected_bit_mask
        comment = (style & comment_bit_mask) == comment_bit_mask
        data = (style & user_bit_mask) > 0
        match = (style & match_bit_mask) == match_bit_mask

        color_registers, h_colors, m_colors, c_colors, d_colors = self.get_colors(segment_viewer, range(32))
        bitimage = np.empty((nr * bytes_per_row, 3), dtype=np.uint8)
        for i in range(32):
            color_is_set = (bytes == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:] = segment_viewer.preferences.empty_background_color[0:3]
        return bitimage.reshape((nr, bytes_per_row, 3))


class JumpmanMachine(Machine):

    ##### Trait initializers

    def _name_default(self):
        return "Jumpman"

    def _bitmap_renderer_default(self):
        return JumpmanPlayfieldRenderer()

    def _mime_prefix_default(self):
        return "application/vnd.atari8bit"


class JumpmanSegmentTable(cg.HexTable):
    def __init__(self, segment, bytes_per_row):
        self.segment = segment
        self.possible_jumpman_segment = ju.is_valid_level_segment(segment)
        self.items_per_row = 160
        self.antic_lines = 88
        self.playfield = self.get_playfield_segment()
        self.pick_buffer = np.zeros((self.items_per_row * self.antic_lines), dtype=np.int32)
        cg.HexTable.__init__(self, self.playfield, self.playfield.style, self.items_per_row, 0x7000)

    def get_label_at_index(self, index):
        return (index // 40)

    def init_level_builder(self, segment_viewer):
        self.segment_viewer = segment_viewer
        self.level_builder = ju.JumpmanLevelBuilder(self.segment_viewer.document.user_segments)
        self.trigger_root = None
        self.cached_screen = None
        self.valid_level = False
        self.force_refresh = True
        self.screen_state = None
        self.trigger_state = None
        self.generate_display_objects()
        self.level_colors = self.calc_level_colors()
        self.draw_playfield(True)

    @property
    def mouse_mode(self):
        return self.segment_viewer.control.mouse_mode

    def generate_display_objects(self, resync=False):
        try:
            source, level_addr, harvest_addr = self.get_level_addrs()
            index = level_addr - source.start_addr
            self.level_builder.parse_level_data(source, level_addr, harvest_addr)
            self.force_refresh = True
            self.valid_level = True
            if self.trigger_root is not None:
                self.trigger_root = self.level_builder.find_equivalent_peanut(self.trigger_root)
                self.trigger_list.recalc_view()
            if resync:
                self.mouse_mode.resync_objects()
        except RuntimeError:
            self.valid_level = False

    def get_playfield(self):
        data = np.empty(self.items_per_row * self.antic_lines, dtype=np.uint8)
        return data

    def get_playfield_segment(self, playfield=None):
        if playfield is None:
            playfield = self.get_playfield()
        r = SegmentData(playfield)
        return DefaultSegment(r, 0x7000)

    def clear_playfield(self, playfield=None):
        if playfield is None:
            playfield = self.playfield
        playfield[:] = 8  # background is the 9th ANTIC color register (counting from zero)
        playfield.style[:] = 0

    def calc_level_colors(self):
        if self.valid_level:
            colors = self.segment[0x2a:0x33].copy()
            # on some levels, the bombs are set to color 0 because they are
            # cycled to produce a glowing effect, but that's not visible here
            # so we force it to be bright white
            fg = colors[4:8]
            fg[fg == 0] = 15
        else:
            colors = powerup_colors()
        return list(colors)

    def get_level_addrs(self):
        if not self.possible_jumpman_segment:
            raise RuntimeError
        source = self.segment
        start = source.start_addr
        level_addr = source[0x37] + source[0x38]*256
        harvest_addr = source[0x4e] + source[0x4f]*256
        log.debug("level def table: %x, harvest table: %x" % (level_addr, harvest_addr))
        last = source.start_addr + len(source)
        if level_addr > start and harvest_addr > start and level_addr < last and harvest_addr < last:
            return source, level_addr, harvest_addr
        raise RuntimeError

    def set_trigger_root(self, root):
        if root is not None:
            root = self.level_builder.find_equivalent_peanut(root)
        self.trigger_root = root
        self.force_refresh = True
        self.trigger_state = None

    def get_screen_state(self):
        if self.trigger_state is not None:
            return self.trigger_state
        return self.screen_state

    def set_current_screen(self, screen=None):
        if screen is None:
            screen = self.playfield
        self.data = screen
        self.style = screen.style

    def redraw_current(self, screen, overlay_objects=[]):
        self.clear_playfield(screen)
        self.pick_buffer[:] = -1
        self.level_builder.set_harvest_offset(self.mouse_mode.get_harvest_offset())
        main_state = self.level_builder.draw_objects(screen, None, self.segment, highlight=overlay_objects, pick_buffer=self.pick_buffer)
        log.debug("draw objects: %s" % self.level_builder.objects)
        if main_state.missing_object_codes:
            log.error("missing draw codes: %s" % (sorted(main_state.missing_object_codes)))
        if self.trigger_root is not None:
            self.level_builder.fade_screen(screen)
            root = [self.trigger_root]
            self.level_builder.draw_objects(screen, root, self.segment, highlight=root, pick_buffer=self.pick_buffer)
            # change highlight to comment color for selected trigger peanut so
            # you don't get confused with any objects actually selected
            old_highlight = np.where(screen.style == selected_bit_mask)
            screen.style[old_highlight] |= comment_bit_mask
            screen.style[:] &= (0xff ^ (match_bit_mask|selected_bit_mask))

            # replace screen state so that the only pickable objects are
            # those in the triggered layer
            self.pick_buffer[:] = -1
            trigger_state = self.level_builder.draw_objects(screen, self.trigger_root.trigger_painting, self.segment, highlight=overlay_objects, pick_buffer=self.pick_buffer)
            active_state = trigger_state
        else:
            active_state = main_state
            trigger_state = None
        return main_state, trigger_state, active_state

    def compute_image(self, force=False):
        if force:
            self.force_refresh = True
        if self.force_refresh:
            self.screen_state, self.trigger_state, _ = self.redraw_current(self.playfield)
            self.cached_screen = self.playfield[:].copy()
            self.force_refresh = False
            self.segment_viewer.update_harvest_state()
        else:
            self.playfield[:] = self.cached_screen
        self.set_current_screen()
        return

    def bad_image(self):
        self.playfield[:] = 0
        self.playfield.style[:] = 0
        self.force_refresh = True
        s = self.playfield.style.reshape((self.antic_lines, -1))
        s[::2,::2] = comment_bit_mask
        s[1::2,1::2] = comment_bit_mask
        self.set_current_screen()
        return

    def draw_playfield(self, force=False):
        if self.valid_level:
            override = self.mouse_mode.calc_playfield_override()
            if override is not None:
                self.set_current_screen(override)
                return
            self.compute_image()
        else:
            self.bad_image()
        self.mouse_mode.draw_extra_objects(self.level_builder, self.playfield, self.segment_viewer.segment)
        # self.mouse_mode.draw_overlay(bitimage)  # FIXME!

    ##### Object edit

    def get_save_location(self):
        if self.trigger_root is not None:
            equiv = self.level_builder.find_equivalent_peanut(self.trigger_root)
            parent = equiv.trigger_painting
        else:
            parent = None
        return parent

    def delete_objects(self, objects):
        save_location = self.get_save_location()
        self.level_builder.delete_objects(objects, save_location)
        self.save_changes()

    def save_objects(self, objects, command_cls=jc.CreateObjectCommand):
        save_location = self.get_save_location()
        self.level_builder.add_objects(objects, save_location)
        self.save_changes(command_cls)

    def save_changes(self, command_cls=jc.MoveObjectCommand):
        source, level_addr, old_harvest_addr = self.get_level_addrs()
        level_data, harvest_addr, ropeladder_data, num_peanuts = self.level_builder.create_level_definition(level_addr, source[0x46], source[0x47])
        index = level_addr - source.start_addr
        ranges = [(0x18,0x2a), (0x3e,0x3f), (0x4e,0x50), (index,index + len(level_data))]
        pdata = np.empty([1], dtype=np.uint8)
        if self.segment_viewer.peanut_harvest_diff < 0:
            pdata[0] = num_peanuts
        else:
            pdata[0] = max(0, num_peanuts - self.segment_viewer.peanut_harvest_diff)
        hdata = np.empty([2], dtype=np.uint8)
        hdata.view(dtype="<u2")[0] = harvest_addr
        data = np.hstack([ropeladder_data, pdata, hdata, level_data])
        cmd = command_cls(source, ranges, data)
        self.segment_viewer.editor.process_command(cmd)

    # Segment saver interface for menu item display
    export_data_name = "Jumpman Level Tester ATR"
    export_extensions = [".atr"]

    def encode_data(self, segment, editor):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        image = get_template("Jumpman Level")
        if image is None:
            raise RuntimeError("Can't find Jumpman Level template file")
        raw = np.fromstring(image, dtype=np.uint8)
        raw[0x0196:0x0996] = segment[:]
        return raw.tostring()


class JumpmanGridControl(BitmapGridControl):
    default_table_cls = JumpmanSegmentTable

    def set_viewer_defaults(self):
        self.items_per_row = 160
        self.zoom = 4
        self.want_col_header = False
        self.want_row_header = False

    def recalc_view_extra_setup(self):
        self.table.init_level_builder(self.segment_viewer)

    def refresh_view(self, *args, **kwargs):
        self.table.draw_playfield(True)
        BitmapGridControl.refresh_view(self, *args, **kwargs)

    def draw_carets(self, dc):
        pass

    ##### popup stuff

    def get_extra_actions(self):
        return []


class JumpmanViewer(BitmapViewer):
    name = "jumpman"

    pretty_name = "Jumpman Level Editor"

    control_cls = JumpmanGridControl

    has_bitmap = True

    has_colors = True

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    ##### Traits

    peanut_harvest_diff = Int(-1)

    num_ladders = Int(-1)

    num_downropes = Int(-1)

    num_peanuts = Int(-1)

    can_select_objects = Bool(False)

    can_erase_objects = Bool(False)

    assembly_source = Str

    custom_code = Any(None)

    manual_recompile_needed = Bool(False)

    old_trigger_mapping = Dict

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

    ##### Initialization and serialization

    def from_metadata_dict_post(self, e):
        # ignore bitmap renderer in restore because we always want to use the
        # JumpmanPlayfieldRenderer in Jumpman level edit mode
        if 'assembly_source' in e:
            self.assembly_source = e['assembly_source']
        if 'old_trigger_mapping' in e:
            self.old_trigger_mapping = e['old_trigger_mapping']

    def to_metadata_dict_post(self, mdict, document):
        mdict["assembly_source"] = self.assembly_source
        mdict["old_trigger_mapping"] = dict(self.old_trigger_mapping)  # so we don't try to pickle a TraitDictObject

    ##### Trait change handlers

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    ##### Jumpman level construction

    def update_harvest_state(self):
        if not self.control.table.valid_level:
            return
        harvest_state = self.control.table.level_builder.get_harvest_state()
        self.num_ladders = len(harvest_state.ladder_positions)
        self.num_downropes = len(harvest_state.downrope_positions)
        self.num_peanuts = len(harvest_state.peanuts)

        # FIXME: force redraw of level data here because it depends on the
        # level builder objects so it can count the number of items
        #self.level_data.refresh_view()
        #self.trigger_list.refresh_view()

    def set_current_draw_pattern(self, pattern, control):
        try:
            iter(pattern)
        except TypeError:
            self.draw_pattern = [pattern]
        else:
            self.draw_pattern = pattern

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
