import os

import wx

import numpy as np
from atrip import Segment, Container, style_bits
from atrip.machines.atari8bit import powerup_colors

from . import parser as ju

import logging
log = logging.getLogger(__name__)
drawlog = logging.getLogger("refresh")


class JumpmanPlayfieldModel:
    def __init__(self, segment):
        self.segment = segment
        self.possible_jumpman_segment = ju.is_valid_level_segment(self.segment)
        self.items_per_row = 160
        self.antic_lines = 88
        self.playfield = self.get_playfield_segment()
        self.pick_buffer = np.zeros((self.items_per_row * self.antic_lines), dtype=np.int32)
        self.coin_harvest_diff = -1
        self.num_ladders = -1
        self.num_downropes = -1
        self.num_coins = -1
        self.can_select_objects = False
        self.can_erase_objects = False
        self.assembly_error = ""
        self.custom_code = None
        self.old_trigger_mapping = {}
        self.trigger_root = None
        self.current_level = None
        self.cached_screen = None
        self.valid_level = False
        self.force_refresh = False
        self.screen_state = None
        self.trigger_state = None
        self.first_time_custom_code_check = True

    @property
    def assembly_source(self):
        return self.segment.assembly_source

    def init_level_builder(self, segment_viewer):
        self.segment_viewer = segment_viewer
        self.segment = segment_viewer.segment
        log.debug(f"init_level_builder: {self.segment}")
        self.possible_jumpman_segment = ju.is_valid_level_segment(self.segment)
        self.level_builder = ju.JumpmanLevelBuilder(self.segment_viewer.document.user_segments)
        self.cached_screen = None
        self.valid_level = False
        self.force_refresh = True
        self.screen_state = None
        self.trigger_state = None
        self.generate_display_objects()
        self.level_colors = self.calc_level_colors()
        self.draw_playfield(True)

        # if assembly source is present but not compiled, only try to compile
        # it once because the call to save_assembly will try to rebuild the
        # data model which continually calls init_level_builder.
        if self.first_time_custom_code_check:
            self.first_time_custom_code_check = False
            if self.assembly_source:
                self.compile_assembly_source()

    @property
    def mouse_mode(self):
        return self.segment_viewer.control.mouse_mode

    def generate_display_objects(self, resync=False):
        try:
            source, level_addr, harvest_addr = self.get_level_addrs()
            index = level_addr - source.origin
            self.level_builder.parse_level_data(source, level_addr, harvest_addr)
            self.force_refresh = True
            self.valid_level = True
            if self.trigger_root is not None:
                self.trigger_root = self.level_builder.find_equivalent_coin(self.trigger_root)
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
        c = Container(playfield)
        return Segment(c, origin=0x7000)

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
        start = source.origin
        level_addr = source[0x37] + source[0x38]*256
        harvest_addr = source[0x4e] + source[0x4f]*256
        log.debug("level def table: %x, harvest table: %x" % (level_addr, harvest_addr))
        last = source.origin + len(source)
        if level_addr > start and harvest_addr > start and level_addr < last and harvest_addr < last:
            return source, level_addr, harvest_addr
        raise RuntimeError

    def set_trigger_root(self, root):
        if root is not None:
            root = self.level_builder.find_equivalent_coin(root)
        log.debug(f"setting trigger root to {root}")
        self.trigger_root = root
        self.force_refresh = True
        self.trigger_state = None

    @property
    def is_editing_trigger(self):
        return self.trigger_root is not None

    def get_screen_state(self):
        if self.trigger_state is not None:
            return self.trigger_state
        return self.screen_state

    def set_current_screen(self, screen=None):
        if screen is None:
            screen = self.playfield
        else:
            self.cached_screen = None
        self.data = screen
        self.style = screen.style

    def redraw_current(self, screen, overlay_objects=[]):
        self.clear_playfield(screen)
        self.pick_buffer[:] = -1
        self.level_builder.set_harvest_offset(self.mouse_mode.get_harvest_offset())
        main_state = self.level_builder.draw_objects(screen, None, self.segment, highlight=overlay_objects, pick_buffer=self.pick_buffer)
        drawlog.debug("draw objects: %s" % self.level_builder.objects)
        drawlog.debug("highlight objects: %s" % overlay_objects)
        if main_state.missing_object_codes:
            log.error("missing draw codes: %s" % (sorted(main_state.missing_object_codes)))
        if self.trigger_root is not None:
            self.level_builder.fade_screen(screen)
            root = [self.trigger_root]
            self.level_builder.draw_objects(screen, root, self.segment, highlight=root, pick_buffer=self.pick_buffer)
            # change highlight to comment color for selected trigger coin so
            # you don't get confused with any objects actually selected
            old_highlight = np.where(screen.style == style_bits.selected_bit_mask)
            screen.style[old_highlight] |= style_bits.comment_bit_mask
            screen.style[:] &= (0xff ^ (style_bits.match_bit_mask|style_bits.selected_bit_mask))

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
        self.set_current_screen()
        if force:
            self.force_refresh = True
        if self.force_refresh or self.cached_screen is None:
            self.screen_state, self.trigger_state, _ = self.redraw_current(self.playfield)
            self.cached_screen = self.playfield[:].copy()
            self.force_refresh = False
            self.update_harvest_state()
        else:
            self.playfield[:] = self.cached_screen
        self.set_current_screen()
        return

    def bad_image(self):
        self.set_current_screen()
        self.playfield[:] = 0
        self.playfield.style[:] = 0
        self.force_refresh = True
        s = self.playfield.container.style.reshape((self.antic_lines, -1))
        s[::2,::2] = style_bits.comment_bit_mask
        s[1::2,1::2] = style_bits.comment_bit_mask
        self.set_current_screen()
        return

    def draw_playfield(self, force=False):
        if self.valid_level:
            override = self.mouse_mode.calc_playfield_override()
            if override is not None:
                drawlog.debug("draw_playfield: using override screen")
                self.set_current_screen(override)
                return
            drawlog.debug("draw_playfield: computing image")
            self.compute_image()
            self.mouse_mode.draw_extra_objects(self.level_builder, self.playfield, self.segment)
        else:
            self.bad_image()
        # self.mouse_mode.draw_overlay(bitimage)  # FIXME!

    ##### Object edit

    def get_save_location(self):
        if self.trigger_root is not None:
            equiv = self.level_builder.find_equivalent_coin(self.trigger_root)
            parent = equiv.trigger_painting
        else:
            parent = None
        return parent

    def delete_objects(self, objects):
        save_location = self.get_save_location()
        self.level_builder.delete_objects(objects, save_location)
        self.segment_viewer.save_changes()

    def save_objects(self, objects):
        save_location = self.get_save_location()
        self.level_builder.add_objects(objects, save_location)
        self.segment_viewer.save_changes(add=True)

    ##### Utilities

    def update_harvest_state(self):
        if not self.current_level.valid_level:
            return
        harvest_state = self.current_level.level_builder.get_harvest_state()
        self.num_ladders = len(harvest_state.ladder_positions)
        self.num_downropes = len(harvest_state.downrope_positions)
        self.num_coins = len(harvest_state.coins)

    def set_current_draw_pattern(self, pattern, control):
        try:
            iter(pattern)
        except TypeError:
            self.draw_pattern = [pattern]
        else:
            self.draw_pattern = pattern

    ##### Custom code handling

    def compile_assembly_source(self):
        log.debug(f"compile_assembly_source: compiling {self.assembly_source}")
        self.custom_code = None
        self.assembly_error = ""
        filename = self.assembly_source
        if not filename:
            return
        self.segment_viewer.editor.metadata_dirty = True
        if not os.path.isabs(filename):
            # relative path; attempt to supply absolute path using document
            d = self.segment_viewer.document
            path = d.filesystem_path()
            if path:
                dirname = os.path.dirname(path)
                filename = os.path.join(dirname, filename)

        try:
            log.debug("compiling jumpman level code in %s" % filename)
            self.custom_code = ju.JumpmanCustomCode(filename)
        except SyntaxError as e:
            self.assembly_error = f"Assembly error:\n{str(e)}"
            log.error(self.assembly_error)
        except ImportError:
            self.assembly_error = f"Assembly error:\nPlease install pyatasm to\ncompile custom code"
            log.error(self.assembly_error)
            self.old_trigger_mapping = dict()
        if self.custom_code:
            self.update_trigger_mapping()
            self.save_assembly()

    @property
    def custom_code_info(self):
        try:
            if self.assembly_error:
                return self.assembly_error
            return self.custom_code.info
        except AttributeError:
            return "No custom code\n"

    @property
    def action_vector_info(self):
        try:
            if self.assembly_error:
                return ""
            return self.custom_code.vector_summary
        except AttributeError:
            return "No custom code\n"

    @property
    def coin_trigger_info(self):
        try:
            if self.assembly_error:
                return ""
            return self.custom_code.coin_trigger_summary
        except AttributeError:
            return "No custom code\n"

    @property
    def other_label_info(self):
        try:
            if self.assembly_error:
                return ""
            return self.custom_code.label_summary
        except AttributeError:
            return "No custom code\n"

    def save_assembly(self):
        log.debug("save_assembly: code=%s" % self.custom_code)
        code = self.custom_code
        if not code:
            return
        source, level_addr, harvest_addr = self.get_level_addrs()
        ranges, data = code.get_ranges(source)
        self.segment_viewer.save_assembly(source, ranges, data)

    def update_trigger_mapping(self):
        # only create old trigger mapping if one doesn't exist
        if not self.old_trigger_mapping:
            self.old_trigger_mapping = dict(self.get_triggers())
        else:
            old_map = self.old_trigger_mapping
            new_map = self.get_triggers()
            if old_map != new_map:
                log.debug("UPDATING trigger map!")
                log.debug("old map %s" % old_map)
                log.debug("new_map %s" % new_map)
                self.current_level.update_triggers(old_map, new_map)
                # FIXME: what about undo and the trigger mapping?
                self.current_level.save_changes(AssemblyChangedCommand)
                self.old_trigger_mapping = new_map

    def update_harvest_state(self):
        if not self.valid_level:
            return
        harvest_state = self.level_builder.get_harvest_state()
        self.num_ladders = len(harvest_state.ladder_positions)
        self.num_downropes = len(harvest_state.downrope_positions)
        self.num_coins = len(harvest_state.coins)

    ##### Jumpman coin triggers

    def get_triggers(self):
        code = self.custom_code
        if code is None:
            return {}
        return code.triggers

    def get_trigger_label(self, addr):
        rev_old_map = {v: k for k, v in self.old_trigger_mapping.items()}
        if addr in rev_old_map:
            return rev_old_map[addr]
        return None