from atrip.machines.atari8bit.jumpman.parser import is_valid_level_segment


from ...viewers.actions import ViewerAction, ViewerActionMixin, ViewerListAction, ViewerRadioAction
from ...editors.actions.segment import segment_select
from .. import commands as jc
from .. import mouse_modes as mm

import logging
log = logging.getLogger(__name__)


class clear_trigger(ViewerAction):
    """Remove any trigger function from the selected coin(s).
    
    """
    name = "Clear Trigger Function"
    enabled_name = 'can_copy'
    command = jc.ClearTriggerCommand

    def __init__(self, *args, **kwargs):
        ViewerAction.__init__(self, *args, **kwargs)
        self.picked = None

    def calc_enabled(self, action_key):
        return self.viewer.control.mouse_mode.all_objects_are_coins()

    def get_objects(self):
        if self.picked is not None:
            return self.picked
        return self.viewer.control.mouse_mode.objects

    def get_addr(self, event, objects):
        return None

    def permute_object(self, obj, addr):
        obj.trigger_function = addr

    def perform(self, event):
        objects = self.get_objects()
        try:
            addr = self.get_addr(event, objects)
            for o in objects:
                self.permute_object(o, addr)
            self.viewer.linked_base.jumpman_playfield_model.save_changes(self.command)
            self.viewer.control.mouse_mode.resync_objects()
        except ValueError:
            pass


class set_trigger(clear_trigger):
    """Set a trigger function for the selected coin(s).

    If you have used the custom code option, have compiled your code using the
    built-in assembler, *and* your code has labels that start with ``trigger``,
    these will show up in the list that appears when you invoke this action.

    Otherwise, you can specify the hex address of a subroutine.
    """
    name = "Set Trigger Function..."
    command = jc.SetTriggerCommand

    def get_addr(self, event, objects):
        addr = trigger_dialog(event, self.viewer, objects[0])
        if addr is not None:
            return addr
        raise ValueError("Cancelled!")


class select_all(ViewerAction):
    """Select all drawing elements in the main level

    """
    name = 'Select All'
    accelerator = 'Ctrl+A'
    tooltip = 'Select the entire document'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_all()


class select_none(ViewerAction):
    """Clear all selections

    """
    name = 'Select None'
    accelerator = 'Shift+Ctrl+A'
    tooltip = 'Clear selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_none()


class select_invert(ViewerAction):
    """Invert the selection; that is: select everything that is currently
    unselected and unselect those that were selected.

    """
    name = 'Invert Selection'
    tooltip = 'Invert selection'
    enabled_name = 'can_select_objects'

    def perform(self, event):
        self.viewer.select_invert()


class flip_vertical(ViewerAction):
    """Flips the selected items top to bottom.

    This calculates the bounding box of just the selected items and uses that
    to find the centerline about which to flip.
    """
    name = "Flip Selection Vertically"
    enabled_name = 'can_copy'
    picked = None
    command = jc.FlipVerticalCommand

    def permute_object(self, obj, bounds):
        obj.flip_vertical(bounds)

    def perform(self, event):
        e = self.editor
        objects = e.bitmap.mouse_mode.objects
        bounds = DrawObjectBounds.get_bounds(objects)
        for o in e.bitmap.mouse_mode.objects:
            self.permute_object(o, bounds)
        e.bitmap.save_changes(self.command)
        e.bitmap.mouse_mode.resync_objects()


class flip_horizontal(flip_vertical):
    """Flips the selected items left to right.

    This calculates the bounding box of just the selected items and uses that
    to find the centerline about which to flip.
    """
    name = "Flip Selection Horizontally"
    command = jc.FlipHorizontalCommand

    def permute_object(self, obj, bounds):
        obj.flip_horizontal(bounds)


class add_assembly_source(ViewerAction):
    """Add an assembly source file to this level (and compile it)

    This is used to provide custom actions or even game loops, beyond what is
    already built-in with trigger painting. There are special labels that are
    recognized by the assembler and used in the appropriate places:

        * vbi1
        * vbi2
        * vbi3
        * vbi4
        * dead_begin
        * dead_at_bottom
        * dead_falling
        * gameloop
        * out_of_lives
        * level_complete
        * collect_callback

    See our `reverse engineering notes
    <http://playermissile.com/jumpman/notes.html#h.s0ullubzr0vv>`_ for more
    details.
    """
    name = 'Custom Code...'

    def perform(self, event):
        linked_base = self.viewer.linked_base
        path = linked_base.frame.prompt_local_file_dialog("Assembly Source File")
        if path is not None:
            linked_base.segment.set_assembly_source(path)


class compile_assembly_source(ViewerAction):
    """Recompile the assembly source code.

    This is a manual action, currently the program doesn't know when the file
    has changed. Making this process more automatic is a planned future
    enhancement.
    """
    name = 'Recompile Code'

    def perform(self, event):
        self.editor.linked_base.jumpman_playfield_model.compile_assembly_source(True)


class jumpman_level_list(ViewerActionMixin, segment_select):
    empty_list_name = "No Jumpman Levels Found"

    def is_valid_segment(self, segment):
        state = is_valid_level_segment(segment)
        log.debug(f"is jumpman level {segment}? {state}")
        return state


class JumpmanMouseModeTool(ViewerRadioAction):
    mouse_mode_cls = None

    def calc_name(self, action_key):
        return self.mouse_mode_cls.menu_item_tooltip

    def calc_icon_name(self, action_key):
        return self.mouse_mode_cls.icon

    def calc_enabled(self, action_key):
        return True

    def calc_checked(self, action_key):
        return self.viewer.control.is_mouse_mode(self.mouse_mode_cls)

    def perform(self, action_key):
        self.viewer.control.set_mouse_mode(self.mouse_mode_cls)


class EraseModeMixin:
    def calc_enabled(self, action_key):
        return self.viewer.current_level.is_editing_trigger

class jumpman_select_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.AnticDSelectMode

class jumpman_draw_girder_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.DrawGirderMode

class jumpman_draw_ladder_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.DrawLadderMode

class jumpman_draw_up_rope_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.DrawUpRopeMode

class jumpman_draw_down_rope_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.DrawDownRopeMode

class jumpman_erase_girder_mode(EraseModeMixin, JumpmanMouseModeTool):
    mouse_mode_cls = mm.EraseGirderMode

class jumpman_erase_ladder_mode(EraseModeMixin, JumpmanMouseModeTool):
    mouse_mode_cls = mm.EraseLadderMode

class jumpman_erase_rope_mode(EraseModeMixin, JumpmanMouseModeTool):
    mouse_mode_cls = mm.EraseRopeMode

class jumpman_draw_coin_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.DrawCoinMode

class jumpman_respawn_mode(JumpmanMouseModeTool):
    mouse_mode_cls = mm.JumpmanRespawnMode
