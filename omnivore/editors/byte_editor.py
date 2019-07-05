# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

# Local imports.
from .tile_manager_base_editor import TileManagerBase
from ..document import DiskImageDocument

from sawx import clipboard
from sawx.filesystem import fsopen
from sawx.utils.processutil import run_detach
from sawx.ui.compactgrid_mouse import DisplayFlags

from atrip.compressor import find_compressors

from .linked_base import LinkedBase
from .. import clipboard_helpers

import logging
log = logging.getLogger(__name__)
clipboard_log = logging.getLogger("clipboard")
event_log = logging.getLogger("event")


class DummyLinkedBase(object):
    segment = None
    segment_uuid = 0

class DummyFocusedViewer(object):
    linked_base = DummyLinkedBase


class ByteEditor(TileManagerBase):
    """Edit binary files

    The views can be restored from data saved in the .omnivore file. The
    metadata file uses the editor name as a keyword into that saved data, so
    multiple editors can save data in the same metadata file without stomping
    over each other.

    The .omnivore file (a JSON file) will contain the editor name as the
    keyword, and editor-specific data below that. Editors should not touch
    anything in the metadata file outside of their keyword, but should save any
    keywords that exist in the file.

    E.g. the file may look like this:

        {
            "omnivore.byte_edit": {
                "layout": {
                    "sidebars": [ ... ],
                    "tile_manager": { .... },
                },
                "viewers": [
                    ...
                ],
                "linked_base_view_segment_uuid" {
                    "uuid1": 0,
                    "uuid2": 3,
                }.
            "omnivore.emulator": {
                ...
            }
        }
    """
    editor_id = "omnivore.byte_edit"
    ui_name = "Byte Editor"

    default_viewers = "hex,bitmap,char,disasm"
    default_viewers = "hex,bitmap,disasm"

    preferences_module = "omnivore.editors.byte_editor_preferences"

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
            None,
            "layout_save",
            ["Restore Layout",
                "layout_restore",
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
            "byte_reverse_group",],
        ["Jumpman",
            ["Edit Level",
                "jumpman_level_list",
            ],
            None,
            "clear_trigger",
            "set_trigger",
            None,
            "add_assembly_source",
            "recompile_assembly_source",
        ],
        ["Generate",
            ["Compression",
                "generate_compression_menu()",
            ],
        ],
        ["Media",
            "generate_segment_menu()",
            None,
            "comment_add",
            "comment_remove",
            None,
            "segment_from_selection",
            "segment_multiple_from_selection",
            "segment_interleave",
            "segment_origin",
            None,
            "segment_goto",
        ],
        ["Machine",
            ["CPU",
                "doc_cpu",
            ],
            ["Operating System",
                "doc_os_labels",
            ],
            ["Assembler Syntax",
                "doc_assembler",
            ],
            None,
            ["Emulator",
                "emu_list",
            ],
            "emu_boot_disk_image",
            "emu_boot_segment",
            "emu_restore",
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
        "byte_set_to_zero": "Ctrl+0",
        "byte_set_to_ff": "Ctrl+9",
        "byte_nop": "Ctrl+3",
        "byte_set_high_bit": "",
        "byte_clear_high_bit": "",
        "byte_bitwise_not": "Ctrl+1",
        "byte_shift_left": "",
        "byte_shift_right": "",
        "byte_rotate_left": "Ctrl+<",
        "byte_rotate_right": "Ctrl+>",
        "byte_reverse_bits": "",
        "byte_random": "",
        "byte_set_value": "",
        "byte_or_with_value": "Ctrl+\\",
        "byte_and_with_value": "Ctrl+7",
        "byte_xor_with_value": "Ctrl+6",
        "byte_ramp_up": "",
        "byte_ramp_down": "",
        "byte_add_value": "Ctrl+=",
        "byte_subtract_value": "Ctrl+-",
        "byte_subtract_from": "Shift+Ctrl+-",
        "byte_multiply_by": "Ctrl+8",
        "byte_divide_by": "Ctrl+/",
        "byte_divide_from": "Shift+Ctrl+/",
        "byte_reverse_selection": "",
        "byte_reverse_group": "",

        "new_file": "Ctrl+N",
        "open_file": "Ctrl+O",
        "save_file" : "Ctrl+S",
        "save_as" : "Shift+Ctrl+S",
        "cut": "Ctrl+X",
        "copy": "Ctrl+C",
        "paste": "Ctrl+V",
        "undo": "Ctrl+Z",
        "redo": "Shift+Ctrl+Z",
        "select_all": "Ctrl+A",
        "select_none": "Shift+Ctrl+A",
        "select_invert": "Ctrl+I",

        "find": "Ctrl+F",
        "prefs": "Ctrl+,",
        "comment_add": "Ctrl+;",
        "comment_remove": "Shift+Ctrl+;",

        "find_to_selection": "Ctrl+T",  # TEST binding
    }

    module_search_order = ["omnivore.viewers.actions", "omnivore.editors.actions", "sawx.actions", "omnivore.jumpman.actions"]

    # Convenience functions

    @property
    def segment(self):
        return self.focused_viewer.linked_base.segment

    @property
    def segments(self):
        return self.document.segments

    @property
    def linked_base(self):
        return self.focused_viewer.linked_base

    @property
    def segment_uuid(self):
        return self.focused_viewer.linked_base.segment_uuid

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def can_copy(self):
        return self.focused_viewer.linked_base.can_copy

    @property
    def current_selection(self):
        return self.focused_viewer.linked_base.current_selection

    #### Initialization

    def __init__(self, document, action_factory_lookup=None):
        TileManagerBase.__init__(self, document, action_factory_lookup)
        self.center_base = None
        self.linked_bases = {}
        self.last_search_settings = {
            "find": "",
            "replace": "",
            "match_case": False,
            "allow_inverse": False,
            "regex": False,
            "algorithm": "",
        }

    @classmethod
    def can_edit_document_exact(cls, document):
        return "atrip_collection" in document.file_metadata

    @classmethod
    def can_edit_document_generic(cls, document):
        return document.mime == "application/octet-stream"

    #### ui

    def generate_segment_menu(self):
        items = []
        for index, container in enumerate(self.document.collection.containers):
            sub_items = [str(container), f"segment_select{{{index}}}"]
            items.append(sub_items)
        return items

    def generate_compression_menu(self):
        items = []
        for index, cls in enumerate(find_compressors()):
            items.append(f"compress_select{{{cls.compression_algorithm}}}")
        items.sort()
        return items

    #### file handling

    def show(self, args=None):
        log.critical(f"show: document {self.document}")
        log.critical(f"show: collection {self.document.collection}")
        log.critical(f"show: segments {self.document.segments}")
        if self.has_command_line_viewer_override(args):
            self.create_layout_from_args(args)
        else:
            s = self.document.last_session.get(self.editor_id, {})
            self.restore_session(s)
        self.restore_legacy_session(self.document.last_session)
        self.set_initial_focused_viewer()
        self.document.recalc_event()

    def create_layout_from_args(self, args):
        log.debug(f"Creating layout from {args}")
        self.center_base = LinkedBase(self)
        self.linked_bases = {self.center_base.uuid:self.center_base}
        viewer_metadata = {}
        for name, value in args.items():
            viewer_metadata[name.strip()] = {}
        self.create_viewers(viewer_metadata)
        self.center_base.view_segment_uuid(None)

    @property
    def layout_template_search_order(self):
        # Try container name, filesystem name
        s = self.center_base.segment
        order = [s.name]
        try:
            order.append(s.filesystem.ui_name)
        except AttributeError:
            pass
        order.append(self.editor_id)
        return order

    def restore_session(self, s):
        log.debug("restore_session: %s" % str(s))
        if 'diff highlight' in s:
            self.diff_highlight = bool(s['diff highlight'])
        self.restore_linked_bases(s)
        self.restore_layout(s)
        # self.restore_view_segment_uuid(s)

    def restore_legacy_session(self, s):
        try:
            container = self.document.collection.containers[0]
        except IndexError:
            pass
        else:
            container.restore_backward_compatible_state(s)

    def restore_linked_bases(self, s):
        linked_bases = {}
        for b in s.get("linked bases", []):
            base = LinkedBase(self)
            base.restore_session(b)
            linked_bases[base.uuid] = base
            log.debug("restore_linked_bases: linked_base[%s]=%s" % (base.uuid, base))
        uuid = s.get("center_base", None)
        log.critical(f"looking for center_base: {uuid}")
        try:
            self.center_base = linked_bases[uuid]
            log.critical(f"found center_base: {self.center_base}")
        except KeyError:
            # no saved session, so find the first interesting segment to display
            segment = self.document.collection.find_interesting_segment_to_edit()
            log.debug(f"most interesting segment: {segment}")
            if segment is None:
                segment = self.document.collection.find_boot_media()
                log.debug(f"default boot media found: {segment}")
            log.debug(f"restoring segment {segment.uuid}")
            self.center_base = LinkedBase(self, segment)
            linked_bases[self.center_base.uuid] = self.center_base

        log.critical(f"linked_bases: {linked_bases}")
        log.critical(f"center_base: {self.center_base}")
        self.linked_bases = linked_bases

    def change_initial_segment(self, ui_name):
        """Change the initial viewed segment to the first one that matches
        the ui_name
        """
        for segment in self.document.collection.iter_segments():
            if segment.ui_name == ui_name:
                log.debug(f"change_initial_segment: changing to segment {segment}")
                self.center_base.view_segment_uuid(segment.uuid, False)
                break

    def rebuild_document_properties(self):
        if not self.document.has_baseline:
            self.use_self_as_baseline(self.document)
        FrameworkEditor.rebuild_document_properties(self)
        b = self.focused_viewer.linked_base
        if b.segment_uuid is None:
            self.document.find_initial_visible_segment(b)
        log.debug("rebuilding document %s; initial segment=%s" % (str(self.document), b.segment))
        self.compare_to_baseline()
        self.can_resize_document = self.document.can_resize

    def init_view_properties(self):
        wx.CallAfter(self.force_focus, self.focused_viewer)
        self.task.machine_menu_changed = self.focused_viewer.machine
        # if self.initial_font_segment:
        #     self.focused_viewer.linked_base.machine.change_font_data(self.initial_font_segment)

    def process_preference_change(self, prefs):
        log.debug("%s processing preferences change" % self.task.name)
        #self.machine.set_text_font(prefs.text_font)

    ##### Copy/paste

    @property
    def supported_clipboard_data(self):
        try:
            return self.focused_viewer.supported_clipboard_data
        except AttributeError:
            return []

    def calc_clipboard_data_from(self, focused):
        print("FOCUSED CONTROL", focused)
        # FIXME: for the moment, assume focused control is in focused viewer
        data_objs = self.focused_viewer.control.calc_clipboard_data_objs(focused)
        return data_objs

    def paste_clipboard(self):
        clipboard_log.debug(f"focused: {self.focused_viewer}")
        data_obj = clipboard.get_clipboard_data(self.supported_clipboard_data)
        if data_obj:
            print("Found data obj", data_obj)
            blob = clipboard_helpers.parse_data_obj(data_obj, self.focused_viewer)
            cmd = self.focused_viewer.calc_paste_command(blob)
            if cmd:
                clipboard_log.debug("processing paste object %s" % cmd)
                self.process_command(cmd)
                return cmd
            # handler = self.get_clipboard_handler(data_obj)
            # if handler:
            #     handler(self, data_obj, focused)
            # else:
            #     clipboard_log.error("No clipboard handler found for data {data_obj}")

    def get_paste_data_from_clipboard(self):
        return clipboard.get_paste_data(self.focused_viewer)

    def process_paste_data(self, serialized_data, cmd_cls=None, *args, **kwargs):
        if cmd_cls is None:
            cmd = self.focused_viewer.get_paste_command(serialized_data, *args, **kwargs)
        else:
            cmd = cmd_cls(self.segment, serialized_data, *args, **kwargs)
        log.debug("processing paste object %s" % cmd)
        self.process_command(cmd)
        return cmd

    #### selection helpers

    def select_all(self):
        self.focused_viewer.select_all()
        self.linked_base.refresh_event(flags=True)

    def select_none(self):
        self.focused_viewer.select_none()
        self.linked_base.refresh_event(flags=True)

    def select_invert(self):
        self.focused_viewer.select_invert()
        self.linked_base.refresh_event(flags=True)

    def check_document_change(self):
        self.document.change_count += 1
        self.update_caret_history()

    def refresh_panes(self):
        log.debug("refresh_panes called")

    def reconfigure_panes(self):
        self.update_pane_names()

    def update_pane_names(self):
        for viewer in self.viewers:
            viewer.update_caption()
        self.control.update_captions()

    def view_segment_uuid(self, uuid):
        base = self.focused_viewer.linked_base
        base.view_segment_uuid(uuid)
        self.update_pane_names()

    def get_extra_segment_savers(self, segment):
        savers = []
        for v in self.viewers:
            savers.extend(v.get_extra_segment_savers(segment))
        return savers

    def save_segment(self, saver, uri):
        try:
            byte_values = saver.encode_data(self.segment, self)
            saver = lambda a,b: byte_values
            self.document.save_to_uri(uri, self, saver, save_metadata=False)
        except Exception as e:
            log.error("%s: %s" % (uri, str(e)))
            #self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            raise

    def show_trace(self):
        """Highlight the current trace after switching to a new segment

        """
        if self.can_trace:
            self.disassembly.update_trace_in_segment()
            self.document.change_count += 1

    ##### Search

    @property
    def search_start(self):
        c = self.focused_viewer.control
        caret = c.caret_handler.current
        index, _ = c.table.get_index_range(caret.rc[0], caret.rc[1])
        return index

    def invalidate_search(self):
        self.task.change_minibuffer_editor(self)

    @property
    def searchers(self):
        search_order = []
        found = set()
        for v in self.viewers:
            for s in v.searchers:
                # searchers may depend on the viewer (like the disassembly)
                # or they may be generic to the segment
                if s.ui_name not in found:
                    search_order.append(s)
                    found.add(s.ui_name)
        log.debug("search order: %s" % [s.ui_name for s in search_order])
        return search_order

    def compare_to_baseline(self):
        if self.diff_highlight and self.document.has_baseline:
            self.document.update_baseline()

    #### command processing

    def calc_status_flags(self):
        return DisplayFlags()

    def process_flags(self, flags):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        event_log.debug(f"process_flags: {self.ui_name}, flags={flags}")
        d = self.document
        visible_range = False

        #self.caret_handler.process_caret_flags(flags, d)

        if flags.message:
            self.frame.status_message(flags.message)

        if flags.metadata_dirty:
            self.metadata_dirty = True

        control = flags.advance_caret_position_in_control
        if control:
            control.post_process_caret_flags(flags)

        control = flags.sync_caret_from_control
        if control:
            self.linked_base.sync_caret_event(flags=flags)

        if flags.data_model_changed:
            event_log.debug(f"process_flags: data_model_changed")
            d.data_model_changed_event(flags=flags)
            d.change_count += 1
            flags.rebuild_ui = True
        elif flags.byte_values_changed:
            event_log.debug(f"process_flags: byte_values_changed")
            d.change_count += 1
            d.byte_values_changed_event(flags=flags)
            flags.refresh_needed = True
        elif flags.byte_style_changed:
            event_log.debug(f"process_flags: byte_style_changed")
            d.change_count += 1
            d.byte_style_changed_event(flags=flags)
            flags.rebuild_ui = True
            flags.refresh_needed = True

        if flags.rebuild_ui:
            event_log.debug(f"process_flags: rebuild_ui")
            d.recalc_event(flags=flags)
        if flags.refresh_needed:
            event_log.debug(f"process_flags: refresh_needed")
            d.recalc_event(flags=flags)
