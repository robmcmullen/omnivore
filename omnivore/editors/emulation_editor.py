# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

# Local imports.
from .byte_editor import ByteEditor
from ..documents.emulation_document import EmulationDocument
from ..emulator import guess_emulator

from sawx.utils.processutil import run_detach

import logging
log = logging.getLogger(__name__)


class EmulationEditor(ByteEditor):
    """Editor that holds an emulator instance and the associated viewers.

    Omnivore can theoretically support multiple views of the same emulator
    where each view could show a different restart number/frame number of the
    emulator. But only one should be in control of the operation at any one
    time. So the state of the emulation document would have to be shared, but
    the current frame number would have to reside here in the editor.
    """

    editor_id = "omnivore.emulator"
    ui_name = "Emulator"

    default_viewers = "hex,bitmap,char,disasm"
    default_viewers = "hex,bitmap,disasm"

    preferences_module = "omnivore.editors.emulation_preferences"

    needs_tabless_frame = True

    menubar_desc = [
        ["File",
            ["New",
                "new_blank_file",
                None,
                "new_file_from_template",
            ],
            "open_file",
            ["Open Recent",
                "open_recent",
            ],
            None,
            "save_file",
            "save_as",
            None,
            "save_as_image",
            "save_animation",
            None,
            "quit",
        ],
        ["Edit",
            "undo",
            "redo",
            None,
            "copy",
            "cut",
            "paste",
            None,
            "select_all",
            "select_none",
            "select_invert",
            ["Mark Selection As",
                "disasm_type",
            ],
            None,
            "find",
            "find_expression",
            "find_next",
            "find_to_selection",
            None,
            "prefs",
        ],
        ["View",
            "view_width",
            "view_zoom",
            ["Colors",
                "view_color_standards",
                None,
                "view_antic_powerup_colors",
                None,
                "view_ask_colors",
            ],
            ["Bitmap",
                "view_bitmap_renderers",
            ],
            ["Text",
                "view_font_renderers",
                None,
                "view_font_mappings",
            ],
            ["Font",
                "view_fonts",
                None,
                "view_font_groups",
                None,
                "view_load_font",
                "view_font_from_selection",
                "view_font_from_segment",
            ],
            None,
            ["Add Data Viewer",
                "view_add_viewer",
            ],
            ["Add Emulation Viewer",
                "view_add_emulation_viewer",
            ],
            None,
            "layout_save_emu",
            ["Restore Emulator Layout",
                "layout_restore_emu",
            ],
            None,
            "show_toolbar",
        ],
        ["Bytes",
            "byte_set_to_zero",
            "byte_set_to_ff",
            "byte_nop",
            None,
            "byte_set_high_bit",
            "byte_clear_high_bit",
            "byte_bitwise_not",
            "byte_shift_left",
            "byte_shift_right",
            "byte_rotate_left",
            "byte_rotate_right",
            "byte_reverse_bits",
            "byte_random",
            None,
            "byte_set_value",
            "byte_or_with_value",
            "byte_and_with_value",
            "byte_xor_with_value",
            None,
            "byte_ramp_up",
            "byte_ramp_down",
            "byte_add_value",
            "byte_subtract_value",
            "byte_subtract_from",
            "byte_multiply_by",
            "byte_divide_by",
            "byte_divide_from",
            None,
            "byte_reverse_selection",
            "byte_reverse_group",
        ],
        ["Media",
            "generate_segment_menu()",
            None,
            "comment_add",
            "comment_remove",
            None,
            "segment_goto",
        ],
        ["Machine",
            "emu_pause_resume",
            "emu_prev_history",
            "emu_next_history",
            None,
            "emu_generate_emulator_specific_key_actions()",
            None,
            "emu_warmstart",
            "emu_coldstart",
        ],
        ["Debug",
            "emu_step",
            "emu_step_into",
            "emu_step_over",
            "emu_break_next_scan_line",
            "emu_break_frame",
            "emu_break_vbi_start",
            "emu_break_vbi_end",
            "emu_break_dli_start",
            "emu_break_dli_end",
        ],
        ["Help",
            "about",
            None,
            "user_guide",
            None,
            "show_debug_log",
            "open_log_directory",
            "open_log",
            None,
            ["Developer Debugging",
                "show_focus",
                "widget_inspector",
                "garbage_objects",
                "raise_exception",
                "test_progress",
            ],
        ],
    ]

    keybinding_desc = {
        "emu_boot_disk_image": "Ctrl+T",  # TEST binding
        "emu_a8_start_key": "F4",
        "emu_a8_select_key": "F3",
        "emu_a8_option_key": "F2",
        "emu_warmstart": "F5",
        "emu_coldstart": "Shift-F5",
        "emu_prev_history": "F6",
        "emu_next_history": "F7",
        "emu_pause_resume": "F8",
        "emu_step": "F9",
        "emu_step_over": "F10",
        "emu_step_out": "F11",
        "emu_break_vbi_start": "shift-F9",
        "emu_break_frame": "F12",

    }

    # Convenience functions

    @property
    def emulator(self):
        return self.document.emulator

    def __init__(self, document, *args, **kwargs):
        ByteEditor.__init__(self, document, *args, **kwargs)
        self.document.boot()

    #### ByteEditor interface

    def prepare_destroy(self):
        self.document.stop_timer()
        ByteEditor.prepare_destroy(self)

    def process_keyword_arguments(self, kwargs):
        doc = self.document
        self.selected_checkpoint_range = None
        if kwargs:
            if "skip_frames" in kwargs:
                doc.skip_frames_on_boot = int(kwargs["skip_frames"])

    def preprocess_document(self, source_document, kwargs):
        if source_document.__class__ == EmulationDocument:
            return source_document
        skip = 0
        log.debug(f"preprocess_document: EmulatorEditor, {source_document}, kwargs={kwargs}")
        kwargs = {}
        try:
            source_document.emulator_type
        except:
            try:
                emulator_type = kwargs['machine']
            except KeyError:
                emulator_type = guess_emulator(source_document)
            doc = EmulationDocument.create_document(source_document=source_document, emulator_type=emulator_type)
        log.debug(f"Using emulator {doc.emulator_type}")
        return doc

    #### images (sawx.editor interface)

    def get_numpy_image(self):
        return self.document.emulator.get_frame_rgb()

    #### animation (sawx.editor interface)

    @property
    def numpy_animation_available(self):
        return self.selected_checkpoint_range is not None

    def get_numpy_animation(self):
        print("ANIMATION RANGE:", self.selected_checkpoint_range)
        start, end = self.selected_checkpoint_range
        if start.frame_number > end.frame_number:
            start, end = end, start
        doc = self.document
        emu = doc.emulator
        frames = []
        save = (emu.current_frame_number, emu.current_restart.restart_number)
        restart_number = end.restart_number
        frame_number = end.frame_number
        while frame_number >= start.frame_number:
            emu.restore_restart(restart_number, frame_number)
            frame = emu.get_frame_rgb(frame_number)
            frame = frame.copy()  # need copy rather than reference to same data storage space
            frames.append(frame)
            frame_number -= 1
        frames.reverse()
        emu.restore_restart(*save)
        return (self.document.framerate, frames)

    #### template

    @property
    def layout_template_search_order(self):
        # search for emulator-specific templates before any generic ones
        order = [self.editor_id + "." + self.document.emulator.name, self.editor_id]
        return order

    #### menu

    def emu_generate_emulator_specific_key_actions(self):
        return self.emulator.get_special_key_actions()
