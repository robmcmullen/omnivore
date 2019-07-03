# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

# Local imports.
from ..editors.byte_editor import ByteEditor
from .document import EmulationDocument
from .. import guess_emulator

from sawx.utils.processutil import run_detach

import logging
log = logging.getLogger(__name__)


class EmulatorEditor(ByteEditor):
    """Editor that holds an emulator instance and the associated viewers.
    """

    editor_id = "omnivore.emulator"
    ui_name = "Emulator"

    default_viewers = "hex,bitmap,char,disasm"
    default_viewers = "hex,bitmap,disasm"

    preferences_module = "omnivore.emulator.preferences"

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
            "emu_step",
            "emu_step_into",
            "emu_step_over",
            "emu_break_frame",
            "emu_break_vbi_start",
            None,
            "emu_generate_emulator_specific_key_actions()",
            None,
            "emu_warmstart",
            "emu_coldstart",
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

    module_search_order = ["omnivore.viewers.actions", "omnivore.editors.actions", "sawx.actions"]

    # Convenience functions

    @property
    def emulator(self):
        return self.document.emulator

    def __init__(self, document, *args, **kwargs):
        ByteEditor.__init__(self, document)

    #### ByteEditor interface

    def prepare_destroy(self):
        self.document.stop_timer()
        ByteEditor.prepare_destroy(self)

    def preprocess_document(self, doc):
        args = {}
        skip = 0
        log.debug(f"preprocess_document: EmulatorEditor, {doc}")
        if self.task_arguments:
            for arg in self.task_arguments.split(","):
                if "=" in arg:
                    arg, v = arg.split("=", 1)
                else:
                    v = None
                args[arg] = v
            if "skip_frames" in args:
                skip = int(args["skip_frames"])
        try:
            doc.emulator_type
        except:
            try:
                emulator_type = args['machine']
            except KeyError:
                emulator_type = guess_emulator(doc)
            doc = EmulationDocument.create_document(source_document=doc, emulator_type=emulator_type, skip_frames_on_boot=skip)
        doc.boot()
        log.debug(f"Using emulator {doc.emulator_type}")
        return doc

    #### menu

    def emu_generate_emulator_specific_key_actions(self):
        return self.emulator.get_special_key_actions()
