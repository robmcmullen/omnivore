# Standard library imports.
import sys
import os
import cPickle as pickle

# Major package imports.
import wx
import numpy as np
from atrcopy import SegmentData, DefaultSegment, selected_bit_mask, comment_bit_mask, user_bit_mask, match_bit_mask

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.api import YES, NO

# Local imports.
from omni8bit.hex_edit.hex_editor import HexEditor
from omni8bit.bitmap_edit.bitmap_editor import MainBitmapScroller, BitmapEditor
from omnivore.framework.document import Document
from omni8bit.arch.machine import Machine, predefined
from omni8bit.arch.colors import powerup_colors
from omni8bit.arch.antic_renderers import BaseRenderer
from omni8bit.ui.bitviewscroller import BitmapScroller
from omni8bit.utils.jumpman import *
from omnivore.templates import get_template

from commands import *
from actions import *
from mouse_modes import *

import logging
log = logging.getLogger(__name__)


class JumpmanLevelView(MainBitmapScroller):
    default_mouse_handler = JumpmanSelectMode

    def __init__(self, *args, **kwargs):
        MainBitmapScroller.__init__(self, *args, **kwargs)
        self.level_builder = None
        self.trigger_root = None
        self.cached_screen = None
        self.valid_level = False
        self.force_refresh = True
        self.screen_state = None
        self.trigger_state = None
    
    def is_ready_to_render(self):
        return self.editor is not None and self.level_builder is not None and self.segment is not None
    
    def on_resize(self, evt):
        # Automatically resize image to a best fit when resized
        if self.is_ready_to_render():
            self.update_zoom()
            self.calc_image_size()
            self.set_scale()

    def update_zoom(self):
        # force zoom so that entire screen fits in window
        w, h = self.GetClientSizeTuple()
        sw = w / 160
        sh = h / 88
        zoom = min(sh, sw)
        self.set_zoom(zoom)

    def set_mouse_mode(self, handler):
        if hasattr(self, 'mouse_mode'):
            self.mouse_mode.cleanup()
        self.release_mouse()
        self.mouse_mode = handler(self)

    def get_segment(self, editor):
        self.level_builder = JumpmanLevelBuilder(editor.document.user_segments)
        self.trigger_root = None
        self.pick_buffer = editor.pick_buffer
        self.force_refresh = True
        self.generate_display_objects()
        return editor.screen

    def generate_display_objects(self, resync=False):
        try:
            source, level_addr, harvest_addr = self.editor.get_level_addrs()
            index = level_addr - source.start_addr
            self.level_builder.parse_level_data(source, level_addr, harvest_addr)
            self.force_refresh = True
            self.valid_level = True
            if self.trigger_root is not None:
                self.trigger_root = self.level_builder.find_equivalent_peanut(self.trigger_root)
                self.editor.trigger_list.recalc_view()
            if resync:
                self.mouse_mode.resync_objects()
        except RuntimeError:
            self.valid_level = False

    def clear_screen(self):
        self.editor.clear_playfield()
        self.pick_buffer[:] = -1

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

    def redraw_current(self, screen, overlay_objects=[]):
        e = self.editor
        e.clear_playfield(screen)
        self.pick_buffer[:] = -1
        self.level_builder.set_harvest_offset(self.mouse_mode.get_harvest_offset())
        main_state = self.level_builder.draw_objects(screen, None, e.segment, highlight=overlay_objects, pick_buffer=self.pick_buffer)
        log.debug("draw objects: %s" % self.level_builder.objects)
        if main_state.missing_object_codes:
            log.error("missing draw codes: %s" % (sorted(main_state.missing_object_codes)))
        if self.trigger_root is not None:
            self.level_builder.fade_screen(screen)
            root = [self.trigger_root]
            self.level_builder.draw_objects(screen, root, e.segment, highlight=root, pick_buffer=self.pick_buffer)
            # change highlight to comment color for selected trigger peanut so
            # you don't get confused with any objects actually selected
            old_highlight = np.where(screen.style == selected_bit_mask)
            screen.style[old_highlight] |= comment_bit_mask
            screen.style[:] &= (0xff ^ (match_bit_mask|selected_bit_mask))

            # replace screen state so that the only pickable objects are
            # those in the triggered layer
            self.pick_buffer[:] = -1
            trigger_state = self.level_builder.draw_objects(screen, self.trigger_root.trigger_painting, e.segment, highlight=overlay_objects, pick_buffer=self.pick_buffer)
            active_state = trigger_state
        else:
            active_state = main_state
            trigger_state = None
        return main_state, trigger_state, active_state

    def compute_image(self, force=False):
        if force:
            self.force_refresh = True
        if self.force_refresh:
            self.screen_state, self.trigger_state, _ = self.redraw_current(self.segment)
            self.cached_screen = self.segment[:].copy()
            self.force_refresh = False
            self.editor.update_harvest_state()
        else:
            self.segment[:] = self.cached_screen

    def bad_image(self):
        self.segment[:] = 0
        self.segment.style[:] = 0
        self.force_refresh = True
        s = self.segment.style.reshape((self.editor.antic_lines, -1))
        s[::2,::2] = comment_bit_mask
        s[1::2,1::2] = comment_bit_mask

    def get_rendered_image(self, segment=None):
        return MainBitmapScroller.get_image(self, segment)

    def get_image(self):
        if self.editor.valid_jumpman_segment:
            override = self.mouse_mode.get_image_override()
            if override is not None:
                return override
        if self.valid_level:
            self.compute_image()
        else:
            self.bad_image()
            bitimage = MainBitmapScroller.get_image(self)
            return bitimage
        self.mouse_mode.draw_extra_objects(self.level_builder, self.segment, self.editor.segment)
        bitimage = MainBitmapScroller.get_image(self)
        self.mouse_mode.draw_overlay(bitimage)
        return bitimage

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

    def save_objects(self, objects, command_cls=CreateObjectCommand):
        save_location = self.get_save_location()
        self.level_builder.add_objects(objects, save_location)
        self.save_changes(command_cls)

    def save_changes(self, command_cls=MoveObjectCommand):
        source, level_addr, old_harvest_addr = self.editor.get_level_addrs()
        level_data, harvest_addr, ropeladder_data, num_peanuts = self.level_builder.create_level_definition(level_addr, source[0x46], source[0x47])
        index = level_addr - source.start_addr
        ranges = [(0x18,0x2a), (0x3e,0x3f), (0x4e,0x50), (index,index + len(level_data))]
        pdata = np.empty([1], dtype=np.uint8)
        if self.editor.peanut_harvest_diff < 0:
            pdata[0] = num_peanuts
        else:
            pdata[0] = max(0, num_peanuts - self.editor.peanut_harvest_diff)
        hdata = np.empty([2], dtype=np.uint8)
        hdata.view(dtype="<u2")[0] = harvest_addr
        data = np.hstack([ropeladder_data, pdata, hdata, level_data])
        cmd = command_cls(source, ranges, data)
        self.editor.process_command(cmd)
    
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

    def get_image(self, m, bytes_per_row, nr, count, bytes, style):
        normal = style == 0
        highlight = (style & selected_bit_mask) == selected_bit_mask
        comment = (style & comment_bit_mask) == comment_bit_mask
        data = (style & user_bit_mask) > 0
        match = (style & match_bit_mask) == match_bit_mask
        
        color_registers, h_colors, m_colors, c_colors, d_colors = self.get_colors(m, range(32))
        bitimage = np.empty((nr * bytes_per_row, 3), dtype=np.uint8)
        for i in range(32):
            color_is_set = (bytes == i)
            bitimage[color_is_set & normal] = color_registers[i]
            bitimage[color_is_set & comment] = c_colors[i]
            bitimage[color_is_set & match] = m_colors[i]
            bitimage[color_is_set & data] = d_colors[i]
            bitimage[color_is_set & highlight] = h_colors[i]
        bitimage[count:,:] = m.empty_color
        return bitimage.reshape((nr, bytes_per_row, 3))


class JumpmanEditor(BitmapEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    valid_jumpman_segment = Bool

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
    
    valid_mouse_modes = [AnticDSelectMode, DrawGirderMode, DrawLadderMode, DrawUpRopeMode, DrawDownRopeMode, DrawPeanutMode, EraseGirderMode, EraseLadderMode, EraseRopeMode, JumpmanRespawnMode]
    
    ##### Default traits
    
    def _machine_default(self):
        return Machine(name="Jumpman", bitmap_renderer=JumpmanPlayfieldRenderer(), mime_prefix="application/vnd.atari8bit")

    def _map_width_default(self):
        return 40 * 4
    
    def _draw_pattern_default(self):
        return [0]
    
    def _valid_jumpman_segment_default(self):
        return False

    def _mouse_mode_default(self):
        return AnticDSelectMode

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################
    
    # Segment saver interface for menu item display
    export_data_name = "Jumpman Level Tester ATR"
    export_extensions = [".atr"]

    def is_valid_for_save(self):
        all_ok = True
        if self.manual_recompile_needed:
            answer = self.task.confirm("Error in assembly code\n\nSave Anyway?" , "Bad Assembly Code")
            all_ok = (answer == YES)
        else:
            self.compile_assembly_source()
        if all_ok and self.custom_code and not self.manual_recompile_needed:
            self.save_assembly()
        if not self.bitmap.level_builder.harvest_ok:
            reason = self.bitmap.level_builder.harvest_reason()
            answer = self.task.confirm("%s\n\nSave Anyway?" % reason, "Bad Peanut Grid")
            all_ok = (answer == YES)
        return all_ok

    def made_current_active_editor(self):
        self.update_mouse_mode(AnticDSelectMode)
        self.refresh_toolbar_state()

    def process_extra_metadata(self, doc, e):
        # ignore bitmap renderer in restore because we always want to use the
        # JumpmanPlayfieldRenderer in Jumpman level edit mode
        if 'bitmap_renderer' in e:
            del e['bitmap_renderer']
        if 'assembly_source' in e:
            self.assembly_source = e['assembly_source']
        if 'old_trigger_mapping' in e:
            self.old_trigger_mapping = e['old_trigger_mapping']
        BitmapEditor.process_extra_metadata(self, doc, e)
        
    def get_extra_metadata(self, mdict):
        mdict["assembly_source"] = self.assembly_source
        mdict["old_trigger_mapping"] = dict(self.old_trigger_mapping)  # so we don't try to pickle a TraitDictObject
        BitmapEditor.get_extra_metadata(self, mdict)

    @on_trait_change('machine.bitmap_shape_change_event')
    def update_bitmap_shape(self):
        self.hex_edit.recalc_view()
        self.bitmap.recalc_view()
    
    @on_trait_change('machine.bitmap_color_change_event')
    def update_bitmap_colors(self):
        try:
            self.bitmap.compute_image(True)
        except RuntimeError:
            pass
        self.bitmap.mouse_mode.resync_objects()
    
    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        pass
    
    @on_trait_change('machine.disassembler_change_event')
    def update_disassembler(self):
        pass

    def set_assembly_source(self, src):
        """Assembly source file is required to be in the same directory as the
        jumpman disk image. It's also assumed to be on the local filesystem
        since pyatasm can't handle the virtual filesystem.
        """
        self.assembly_source = src
        self.manual_recompile_needed = False
        self.compile_assembly_source()

    def compile_assembly_source(self, show_info=False):
        self.custom_code = None
        if not self.assembly_source:
            return
        self.metadata_dirty = True
        path = self.document.filesystem_path()
        if not path:
            if show_info:
                # only display error message on user-initiated compilation
                self.window.error("Please save the level before\ncompiling the assembly source", "Assembly Error")
            return
        dirname = os.path.dirname(self.document.filesystem_path())
        if dirname:
            filename = os.path.join(dirname, self.assembly_source)
            try:
                self.custom_code = JumpmanCustomCode(filename)
                self.manual_recompile_needed = False
            except SyntaxError, e:
                log.error("Assembly error: %s" % e.msg)
                self.window.error(e.msg, "Assembly Error")
                self.manual_recompile_needed = True
            except ImportError:
                log.error("Please install pyatasm to compile custom code.")
                self.assembly_source = ""
                self.old_trigger_mapping = dict()
            if self.custom_code:
                self.update_trigger_mapping()
                if show_info:
                    dlg = wx.lib.dialogs.ScrolledMessageDialog(self.window.control, self.custom_code.info, "Assembly Results")
                    dlg.ShowModal()

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
                self.bitmap.level_builder.update_triggers(old_map, new_map)
                # FIXME: what about undo and the trigger mapping?
                self.bitmap.save_changes(AssemblyChangedCommand)
                self.old_trigger_mapping = new_map

    def get_triggers(self):
        if self.custom_code is None and self.manual_recompile_needed == False:
            self.compile_assembly_source()
        code = self.custom_code
        if code is None:
            return {}
        return code.triggers

    def get_trigger_label(self, addr):
        rev_old_map = {v: k for k, v in self.old_trigger_mapping.iteritems()}
        if addr in rev_old_map:
            return rev_old_map[addr]
        return None

    def save_assembly(self):
        code = self.custom_code
        if not code:
            return
        source, level_addr, harvest_addr = self.get_level_addrs()
        ranges, data = code.get_ranges(source)
        cmd = MoveObjectCommand(source, ranges, data)
        self.process_command(cmd)

    def rebuild_display_objects(self):
        self.bitmap.generate_display_objects(True)
    
    def reconfigure_panes(self):
        self.hex_edit.recalc_view()
        self.bitmap.recalc_view()
        self.level_data.recalc_view()
        self.trigger_list.recalc_view()
    
    def refresh_panes(self):
        self.hex_edit.refresh_view()
        p = self.get_level_colors()
        if p != self.machine.antic_color_registers:
            self.machine.update_colors(p)
        self.bitmap.refresh_view()
        self.trigger_list.refresh_view()
        # level_data is refreshed with call to update_harvest_state
    
    def rebuild_document_properties(self):
        self.update_mouse_mode(AnticDSelectMode)
        self.manual_recompile_needed = False
        self.compile_assembly_source()

    def check_valid_segment(self, segment=None):
        if segment is None:
            segment = self.segment
        # 283f is always 4c (JMP) because it and the next two bytes are a jump target from the game loop
        # 2848: always 20 (i.e. JSR)
        # 284b: always 60 (i.e. RTS)
        # 284c: always FF (target for harvest table if no action to be taken)
        if len(segment) >= 0x800 and segment[0x3f] == 0x4c and segment[0x48] == 0x20 and segment[0x4b] == 0x60 and segment[0x4c] == 0xff:
            # check for sane level definition table
            index = segment[0x38]*256 + segment[0x37] - segment.start_addr
            return index >=0 and index < len(segment)
        return False

    def get_level_addrs(self):
        if not self.valid_jumpman_segment:
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

    def find_first_valid_segment_index(self):
        # Find list of matches meeting minimum criteria
        possible = []
        for i, segment in enumerate(self.document.segments):
            if self.check_valid_segment(segment):
                possible.append(i)
                if len(segment) == 0x800:
                    return i
        if possible:
            return possible[0]
        return 0
    
    def init_view_properties(self):
        self.find_segment()

    def copy_view_properties(self, old_editor):
        segment = old_editor.segment
        if self.check_valid_segment(segment):
            if len(segment) != 0x800:
                segment = None
        self.find_segment(segment=segment)
    
    def view_segment_set_width(self, segment):
        self.valid_jumpman_segment = self.check_valid_segment(segment)
        self.bitmap_width = 40 * 4
        self.machine.update_colors(self.get_level_colors(segment))
        self.update_mouse_mode()
        self.peanut_harvest_diff = -1
    
    def update_harvest_state(self):
        if not self.valid_jumpman_segment:
            return
        harvest_state = self.bitmap.level_builder.get_harvest_state()
        self.num_ladders = len(harvest_state.ladder_positions)
        self.num_downropes = len(harvest_state.downrope_positions)
        self.num_peanuts = len(harvest_state.peanuts)
        
        # FIXME: force redraw of level data here because it depends on the
        # level builder objects so it can count the number of items
        self.level_data.refresh_view()
        self.trigger_list.refresh_view()

    def get_level_colors(self, segment=None):
        if segment is None:
            segment = self.segment
        if self.check_valid_segment(segment):
            colors = segment[0x2a:0x33].copy()
            # on some levels, the bombs are set to color 0 because they are
            # cycled to produce a glowing effect, but that's not visible here
            # so we force it to be bright white
            fg = colors[4:8]
            fg[fg == 0] = 15
        else:
            colors = powerup_colors()
        return list(colors)
    
    def update_mouse_mode(self, mouse_handler=None):
        BitmapEditor.update_mouse_mode(self, mouse_handler)
        self.can_select_objects = self.bitmap.mouse_mode.can_paste
        self.bitmap.refresh_view()
    
    def set_current_draw_pattern(self, pattern, control):
        try:
            iter(pattern)
        except TypeError:
            self.draw_pattern = [pattern]
        else:
            self.draw_pattern = pattern
        if control != self.tile_map:
            self.tile_map.clear_tile_selection()
        if control != self.character_set:
            self.character_set.clear_tile_selection()
    
    def highlight_selected_ranges(self):
        HexEditor.highlight_selected_ranges(self)

    def mark_index_range_changed(self, index_range):
        pass
    
    def perform_idle(self):
        mouse_mode = self.bitmap.mouse_mode
        self.can_copy = self.can_cut = mouse_mode.can_paste and bool(mouse_mode.objects)
    
    def process_paste_data_object(self, data_obj, cmd_cls=None):
        # Don't use bitmap editor's paste, we want it to paste in hex
        return HexEditor.process_paste_data_object(self, data_obj, cmd_cls)
    
    def create_clipboard_data_object(self):
        # Don't use bitmap editor's clipboard, we want hex bytes
        return HexEditor.create_clipboard_data_object(self)
    
    def get_extra_segment_savers(self, segment):
        savers = []
        savers.append(self.bitmap)
        return savers

    def get_playfield(self):
        data = np.empty(40 * 4 * self.antic_lines, dtype=np.uint8)
        return data

    def get_playfield_segment(self, playfield=None):
        if playfield is None:
            playfield = self.get_playfield()
        r = SegmentData(playfield)
        return DefaultSegment(r, 0x7000)

    def clear_playfield(self, playfield=None):
        if playfield is None:
            playfield = self.screen
        playfield[:] = 8  # background is the 9th ANTIC color register
        playfield.style[:] = 0
    
    def undo_post_hook(self):
        self.rebuild_display_objects()
        self.update_mouse_mode()
    
    def redo_post_hook(self):
        self.rebuild_display_objects()
        self.update_mouse_mode()

    ##### Copy/Paste support

    def cut(self):
        """ Cuts the current selection to the clipboard
        """
        if self.copy():
            self.bitmap.mouse_mode.delete_objects()

    def process_paste_data_object(self, data_obj, cmd_cls=None):
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste:
            value = data_obj.GetData()
            fmt = data_obj.GetPreferredFormat()
            if fmt.GetId() == "jumpman,objects":
                objects = pickle.loads(value)
                for o in objects:
                    # offset slightly so the pasted objects are seen
                    o.x += 1
                    o.y += 1
                mouse_mode.objects = objects
                self.bitmap.save_objects(objects)
    
    supported_clipboard_data_objects = [
        wx.CustomDataObject("jumpman,objects"),
        ]
    
    def create_clipboard_data_object(self):
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste and mouse_mode.objects:
            data = mouse_mode.objects
            data_obj = wx.CustomDataObject("jumpman,objects")
            data_obj.SetData(pickle.dumps(data))
            return data_obj
        return None

    def select_all(self, refresh=True):
        """ Selects the entire document
        """
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste:
            first = True
            for obj in self.bitmap.level_builder.objects:
                mouse_mode.add_to_selection(obj, not first)
                first = False
            if refresh:
                self.refresh_panes()

    def select_none(self, refresh=True):
        """ Clears any selection in the document
        """
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste:
            mouse_mode.objects = []
            if refresh:
                self.refresh_panes()

    def select_invert(self, refresh=True):
        """ Selects the entire document
        """
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste:
            first = True
            current = set(mouse_mode.objects)
            for obj in self.bitmap.level_builder.objects:
                if obj not in current:
                    mouse_mode.add_to_selection(obj, not first)
                    first = False
            if refresh:
                self.refresh_panes()

    def set_trigger_view(self, trigger_root):
        mouse_mode = self.bitmap.mouse_mode
        if mouse_mode.can_paste:
            mouse_mode.objects = []
        self.bitmap.set_trigger_root(trigger_root)
        self.can_erase_objects = trigger_root is not None
        self.refresh_panes()
        self.refresh_toolbar_state()

    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.bitmap = JumpmanLevelView(parent, self.task)

        self.antic_lines = 88
        self.screen = self.get_playfield_segment()
        self.pick_buffer = np.zeros((160 * self.antic_lines), dtype=np.int32)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.segment_list = self.window.get_dock_pane('jumpman.segments').control
        self.undo_history = self.window.get_dock_pane('jumpman.undo').control
        self.hex_edit = self.window.get_dock_pane('jumpman.hex').control
        self.level_data = self.window.get_dock_pane('jumpman.level_data').control
        self.trigger_list = self.window.get_dock_pane('jumpman.triggers').control

        # Load the editor's contents.
        self.load()

        return self.bitmap

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        if control != self.hex_edit:
            self.hex_edit.select_index(index)
