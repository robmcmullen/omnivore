# Standard library imports.
import sys
import os

# Major package imports.
import numpy as np
from atrip import style_bits
from atrip.machines.atari8bit.jumpman import parser as jp

# Local imports.
from sawx.utils.command import Overlay

from . import commands as jc
from ..viewers.mouse_modes import NormalSelectMode

import logging
log = logging.getLogger(__name__)
selectlog = logging.getLogger("select")

class JumpmanSelectMode(NormalSelectMode):
    can_paste = False

    def __init__(self, *args, **kwargs):
        NormalSelectMode.__init__(self, *args, **kwargs)
        self.mouse_down = (0, 0)
        self.objects = []

    def cleanup(self):
        pass

    def resync_objects(self):
        pass

    def all_objects_are_coins(self):
        if self.objects:
            state = True
            for obj in self.objects:
                if not obj.single:
                    state = False
                    break
        else:
            state = False
        return state

    def calc_playfield_override(self):
        """ Replace the entire bit image generation in JumpmanLevelView """
        return None

    def draw_extra_objects(self, lever_builder, screen, current_segment):
        return

    def draw_overlay(self, bitimage):
        return

    def get_harvest_offset(self):
        source = self.control.segment_viewer.segment
        if len(source) < 0x47:
            hx = hy = 0, 0
        else:
            hx = source[0x46]
            hy = source[0x47]
        return hx, hy

    def draw_harvest_grid(self, screen):
        hx, hy = self.get_harvest_offset()
        w = 160
        h = 88

        # Original (slow) algorithm to determine bad locations:
        #
        # def is_allergic(x, y, hx, hy):
        #     return (x + 0x30 + hx) & 0x1f < 7 or (2 * y + 0x20 + hy) & 0x1f < 5
        #
        # Note that in the originial 6502 code, the y coord is in player
        # coords, which is has twice the resolution of graphics 7. That's the
        # factor of two in the y part. Simplifying, the bad locations can be
        # defined in sets of 32 columns and 16 rows:
        #
        # x: 16 - hx, 16 - hx + 6 inclusive
        # y: 0 - hy/2, 0 - hy/2 + 2 inclusive
        hx = hx & 0x1f
        hy = (hy & 0x1f) // 2
        startx = (16 - hx) & 0x1f
        starty = (0 - hy) & 0xf

        # Don't know how to set multiple ranges simultaneously in numpy, so use
        # a slow python loop
        s = screen._style.reshape((h, w))
#        s[:] = 0
        for x in range(startx, startx + 8):
            x = x & 0x1f
            s[0:h:, x::32] |= style_bits.comment_bit_mask
        for y in range(starty, starty + 4):
            y = y & 0xf
            s[y:h:16,:] |= style_bits.comment_bit_mask

    def get_xy(self, evt):
        c = self.control
        y, x, _ = c.get_row_col_from_event(evt)
        if y < c.model.antic_lines:
            index, _ = c.table.get_index_range(y, x)
            pick = c.model.pick_buffer[index]
        else:
            pick = -1
        return x, y, pick

    def display_coords(self, evt, extra=None):
        c = self.control
        e = c.segment_viewer
        if e is not None:
            x, y, pick = self.get_xy(evt)
            msg = "x=%d (0x%x) y=%d (0x%x) pick=%d" % (x, x, y, y, pick)
            if extra:
                msg += " " + extra
            e.linked_base.editor.frame.status_message(msg)

    def process_left_down(self, evt):
        self.display_coords(evt)

    def process_left_up(self, evt):
        self.display_coords(evt)

    def process_left_dclick(self, evt):
        pass

    def process_mouse_motion_down(self, evt):
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)

    def get_picked(self, pick):
        return self.control.model.screen_state.get_picked(pick)

    def calc_popup_data(self, evt):
        cg = self.control
        row, col, _ = cg.get_row_col_from_event(evt)
        inside = True  # fixme
        style = 0
        obj = self.objects
        if len(obj) == 0:
            x, y, pick = self.get_xy(evt)
            if pick >= 0:
                p = self.get_picked(pick)
                if p.single:
                    obj = [p]
                else:
                    obj = None
            else:
                obj = None
        popup_data = {
            'index': None,
            'in_selection': style&0x80,
            'row': row,
            'col': col,
            'inside': inside,
            'jumpman_obj': obj,
            }
        return popup_data

    def calc_popup_actions(self, evt, data):
        obj = data['jumpman_obj']
        if obj is not None:
            clearable = any(o.trigger_function is not None for o in obj)
        else:
            clearable = False
        # clear_trigger = jc.ClearTriggerAction(enabled=obj is not None and clearable, picked=obj, task=self.control.segment_viewer.linked_base.task)
        # trigger_action = jc.SetTriggerAction(enabled=obj is not None, picked=obj, task=self.control.segment_viewer.linked_base.task)
        actions = ["clear_trigger", "trigger_action", None, "cut", "copy", "paste", None, "select_all", "select_none", "select_invert"]
        return actions


class AnticDSelectMode(JumpmanSelectMode):
    icon = "cursor"
    menu_item_name = "Select"
    menu_item_tooltip = "Select regions"
    min_mouse_distance = 2
    can_paste = True

    def init_post_hook(self):
        self.pending_remove = None
        self.override_state = None

    def resync_objects(self):
        """ After a redraw when the level builder has been rebuilt from the hex
        data, the objects stored locally will no longer point to current
        jumpman objects. We need to find the current objects that match up to
        the stored objects.
        """
        selectlog.debug("before resyncing: %s" % self.objects)
        self.objects = self.control.model.level_builder.find_equivalent(self.objects)
        selectlog.debug("after resyncing: %s" % self.objects)

    def delete_objects(self):
        if self.objects:
            self.control.model.delete_objects(self.objects)
            self.objects = []
        self.control.Refresh()

    def calc_playfield_override(self):
        if not self.objects:
            self.override_state = None
            return

        model = self.control.model
        playfield = model.get_playfield_segment()  # use new, temporary playfield
        _, _, self.override_state = model.redraw_current(playfield, self.objects)
        log.debug("override_state: %s" % self.override_state)

        # Draw the harvest grid if a coin is selected
        for obj in self.objects:
            if obj.single:
                self.draw_harvest_grid(playfield)
                break
        return playfield

    def get_picked(self, pick):
        if self.override_state:
            state = self.override_state
        else:
            state = self.control.model.get_screen_state()
        if state is not None:
            return state.get_picked(pick)
        else:
            raise ValueError("Invalid state")

    def highlight_pick(self, evt):
        x, y, pick = self.get_xy(evt)
        self.mouse_down = x, y
        if pick >= 0:
            obj = self.get_picked(pick)
            selectlog.debug("picked object: %s" % obj)
            if obj in self.objects:
                if evt.ControlDown():
                    self.pending_remove = obj
                else:
                    self.pending_remove = True
            else:
                self.add_to_selection(obj, evt.ControlDown())
            self.check_tolerance = True
        else:
            # don't kill multiple selection if user clicks on empty space by
            # mistake
            if not evt.ControlDown():
                self.objects = []

    def add_to_selection(self, obj, append=False):
        obj.orig_x = int(obj.x)
        obj.orig_y = int(obj.y)
        if append:
            self.objects.append(obj)
        else:
            self.objects = [obj]

    def move_pick(self, evt):
        if self.objects:
            x, y, pick = self.get_xy(evt)
            dx = x - self.mouse_down[0]
            dy = y - self.mouse_down[1]
            if self.check_tolerance and abs(dx) + abs(dy) <  self.min_mouse_distance:
                return
            self.check_tolerance = False
            for obj in self.objects:
                selectlog.debug("moving %s, equiv %s" % (obj, self.control.model.level_builder.find_equivalent_object(obj)))
                obj.x = obj.orig_x + dx
                obj.x &= obj.valid_x_mask
                obj.y = obj.orig_y + dy
            self.pending_remove = None

    def process_left_down(self, evt):
        selectlog.debug("left down: %s" % evt)
        try:
            self.highlight_pick(evt)
        except ValueError:
            pass
        else:
            self.control.refresh_view()
            self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        if self.objects:
            self.move_pick(evt)
            self.control.refresh_view()
        self.display_coords(evt)

    def process_left_up(self, evt):
        if self.num_clicks == 2:
            return
        selectlog.debug("pending_remove: %s" % self.pending_remove)
        if self.pending_remove is True:
            self.objects = []
        elif self.pending_remove is not None:
            self.objects.remove(self.pending_remove)
        self.pending_remove = None
        if self.objects and not self.check_tolerance:
            self.control.segment_viewer.save_changes()
            self.resync_objects()
            self.control.refresh_view()
        else:
            self.control.refresh_view()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.display_coords(evt)

    def check_trigger_pick(self, evt):
        x, y, pick = self.get_xy(evt)
        if pick >= 0:
            obj = self.get_picked(pick)
            if obj.single:
                self.control.segment_viewer.set_trigger_view(obj)

    def process_left_dclick(self, evt):
        try:
            self.check_trigger_pick(evt)
        except ValueError:
            pass
        evt.Skip()

    def delete_key_pressed(self):
        self.delete_objects()

    def backspace_key_pressed(self):
        self.delete_objects()

    def get_popup_actions(self, evt):
        return self.get_trigger_popup_actions(evt)


class DrawMode(JumpmanSelectMode):
    icon = "cursor"
    menu_item_name = "Draw"
    menu_item_tooltip = "Draw stuff"
    drawing_object = jp.Girder
    can_paste = False

    def resync_objects(self):
        # objects here are only temporary, so no need to search
        pass

    def draw_extra_objects(self, level_builder, screen, current_segment):
        level_builder.draw_objects(screen, self.objects, current_segment)

    def create_objects(self, evt, start=False):
        c = self.control
        e = c.segment_viewer
        if e is None:
            return
        x, y, pick = self.get_xy(evt)
        if start:
            self.mouse_down = x, y
        dx = x - self.mouse_down[0]
        dy = y - self.mouse_down[1]
        obj = self.drawing_object
        if obj.vertical_only:
            sx = 0
            sy = obj.default_dy if dy > 0 else -obj.default_dy
            num = max((dy + sy - 1) // sy, 1)
        elif obj.single:
            sx = obj.default_dx
            sy = 0
            num = 1
        else:
            if abs(dx) >= abs(dy):
                sx = obj.default_dx if dx > 0 else -obj.default_dx
                num = max((abs(dx) + abs(sx) - 1) // abs(sx), 1)
                sy = dy // num
            else:
                sy = obj.default_dy if dy > 0 else -obj.default_dy
                num = max((abs(dy) + abs(sy) - 1) // abs(sy), 1)
                sx = dx // num
        screen_x = (self.mouse_down[0] - obj.default_dx // 2) & obj.valid_x_mask
        screen_y = self.mouse_down[1] - obj.default_dy // 2

        self.objects = []
        item = obj(-1, screen_x, screen_y, num, sx, sy)
        if not item.is_offscreen():
            self.objects.append(item)
        self.check_objects(x, y)

    def check_objects(self, x, y):
        pass

    def process_left_down(self, evt):
        self.create_objects(evt, True)
        self.control.refresh_view()
        self.display_coords(evt)

    def process_left_up(self, evt):
        if self.num_clicks == 2:
            return
        log.debug("saving objects: %s" % self.objects)
        self.control.model.save_objects(self.objects)
        self.objects = []
        self.control.refresh_view()
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.create_objects(evt)
        self.control.refresh_view()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.create_objects(evt, True)
        self.control.refresh_view()
        self.display_coords(evt)


class DrawGirderMode(DrawMode):
    icon = "jumpman_girder"
    menu_item_name = "Draw Girder"
    menu_item_tooltip = "Draw girders"
    drawing_object = jp.Girder


class DrawLadderMode(DrawMode):
    icon = "jumpman_ladder"
    menu_item_name = "Draw Ladder"
    menu_item_tooltip = "Draw ladders (vertical only)"
    drawing_object = jp.Ladder


class DrawUpRopeMode(DrawMode):
    icon = "jumpman_uprope"
    menu_item_name = "Draw Up Rope"
    menu_item_tooltip = "Draw up ropes (vertical only)"
    drawing_object = jp.UpRope


class DrawDownRopeMode(DrawMode):
    icon = "jumpman_downrope"
    menu_item_name = "Draw Down Rope"
    menu_item_tooltip = "Draw down ropes (vertical only)"
    drawing_object = jp.DownRope


class EraseGirderMode(DrawMode):
    icon = "jumpman_erase_girder"
    menu_item_name = "Erase Girder"
    menu_item_tooltip = "Erase girders"
    drawing_object = jp.EraseGirder
    editor_trait_for_enabled = 'focused_viewer.can_erase_objects'


class EraseLadderMode(DrawMode):
    icon = "jumpman_erase_ladder"
    menu_item_name = "Erase Ladder"
    menu_item_tooltip = "Erase ladders (vertical only)"
    drawing_object = jp.EraseLadder
    editor_trait_for_enabled = 'focused_viewer.can_erase_objects'


class EraseRopeMode(DrawMode):
    icon = "jumpman_erase_rope"
    menu_item_name = "Erase Rope"
    menu_item_tooltip = "Erase ropes (vertical only)"
    drawing_object = jp.EraseRope
    editor_trait_for_enabled = 'focused_viewer.can_erase_objects'


class DrawCoinMode(DrawMode):
    icon = "jumpman_coin"
    menu_item_name = "Draw Coins"
    menu_item_tooltip = "Draw coins (single only)"
    drawing_object = jp.Coin

    def __init__(self, *args, **kwargs):
        DrawMode.__init__(self, *args, **kwargs)
        self.is_bad_location = False
        self.batch = None

    def cleanup(self):
        self.control.segment_viewer.screen.style[:] = 0

    def get_caret(self):
        if self.is_bad_location:
            return wx.Cursor(wx.CURSOR_HAND)
        else:
            return wx.Cursor(wx.CURSOR_ARROW)

    def check_objects(self, x, y):
        hx, hy = self.get_harvest_offset()
        if self.objects:
            self.is_bad_location = self.objects[0].is_bad_location(hx, hy)
        else:
            self.is_bad_location = jp.is_bad_harvest_position(x, y, hx, hy)

    def draw_extra_objects(self, level_builder, screen, current_segment):
        if self.objects:
            obj = self.objects[0]
            obj.error = self.is_bad_location
            if not obj.error:
                hx, hy = self.get_harvest_offset()
                grid = obj.harvest_checksum(hx, hy)
                obj.error = grid in level_builder.harvest_offset_seen
        level_builder.draw_objects(screen, self.objects, current_segment)
        self.draw_harvest_grid(screen)

    def change_harvest_offset(self, evt, start=False):
        c = self.control
        e = c.segment_viewer
        if e is None:
            return
        x, y, pick = self.get_xy(evt)
        if start:
            self.batch = Overlay()
            hx, hy = self.get_harvest_offset()
            self.mouse_down = hx + x, hy + y
        else:
            dx = (self.mouse_down[0] - x) & 0x1f
            dy = ((self.mouse_down[1] - y) & 0xf) * 2
            self.display_coords(evt)
            values = [dx, dy]
            cmd = ChangeByteCommand(e.segment, 0x46, 0x48, values)
            e.editor.process_command(cmd, self.batch)

    def process_left_down(self, evt):
        self.create_objects(evt, True)
        if self.is_bad_location:
            self.change_harvest_offset(evt, True)
            self.objects = []
        else:
            self.control.Refresh()
        self.display_coords(evt)

    def process_left_up(self, evt):
        if self.num_clicks == 2:
            return
        if self.batch is not None:
            c = self.control
            e = c.segment_viewer
            if e is None:
                return
            e.editor.end_batch()
            self.batch = None

            # Force updating of the hex view
            e.document.change_count += 1
            e.linked_base.refresh_event(True)
        else:
            DrawMode.process_left_up(self, evt)
            return
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        if self.batch is not None:
            self.change_harvest_offset(evt)
        else:
            self.create_objects(evt)
            self.control.refresh_view()
        self.display_coords(evt)

    def process_mouse_motion_up(self, evt):
        self.create_objects(evt, True)
        self.control.refresh_view()
        self.display_coords(evt)

    def get_popup_actions(self, evt):
        return self.get_trigger_popup_actions(evt)


class JumpmanRespawnMode(DrawMode):
    icon = "jumpman_respawn"
    menu_item_name = "Set Jumpman Start"
    menu_item_tooltip = "Set jumpman respawn position"
    drawing_object = jp.JumpmanRespawn

    def init_post_hook(self):
        x, y = self.get_respawn_point()
        self.current = self.drawing_object(-1, x, y, 1, 0, 0)
        self.objects = []

    def get_respawn_point(self):
        source = self.control.segment_viewer.segment
        x = source[0x39]
        y = source[0x3a]
        return x - 0x30, (y - 0x18) // 2

    def draw_extra_objects(self, level_builder, screen, current_segment):
        objects = [self.current]
        objects.extend(self.objects)
        level_builder.draw_objects(screen, objects, current_segment)

    def change_jumpman_respawn(self, evt):
        obj = self.objects[0]
        values = [obj.x + 0x30, (obj.y * 2) + 0x18]
        self.control.segment_viewer.linked_base.change_bytes(0x39, 0x3b, values, "Change Respawn Point")

    def process_left_up(self, evt):
        if self.num_clicks == 2:
            return
        self.change_jumpman_respawn(evt)
        self.init_post_hook()
        self.display_coords(evt)

    def process_mouse_motion_down(self, evt):
        self.process_mouse_motion_up(evt)
