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

from omnivore_framework.utils.processutil import run_detach

from .linked_base import LinkedBase
from .byte_editor_preferences import ByteEditorPreferences

import logging
log = logging.getLogger(__name__)


class DummyLinkedBase(object):
    segment = None
    segment_number = 0

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
                "linked_base_view_segment_number" {
                    "uuid1": 0,
                    "uuid2": 3,
                }.
            "omnivore.emulator": {
                ...
            }
        }
    """
    name = "omnivore.byte_edit"
    pretty_name = "Byte Editor"

    extra_metadata_file_extensions = ["omnivore"]

    default_viewers = "hex,bitmap,char,disasm"

    preferences_module = "omnivore.editors.byte_editor_preferences"

    menubar_desc = [
    ["File", "new_file", "open_file", ["Open Recent", "open_recent"], None, "save_file", "save_as", None, "quit"],
    ["Edit", "undo", "redo", None, "copy", "cut", "paste", None, "select_all", "select_none", "select_invert", None, "prefs"],
    ["View", "view_width", "view_zoom", ["Colors", "view_ntsc", "view_pal", None, "view_antic_powerup_colors", None, "view_ask_colors"]],
    ["Bytes", "byte_set_to_zero", "byte_set_to_ff", "byte_nop", None, "byte_set_high_bit", "byte_clear_high_bit", "byte_bitwise_not", "byte_shift_left", "byte_shift_right", "byte_rotate_left", "byte_rotate_right", "byte_reverse_bits", "byte_random", None, "byte_set_value", "byte_or_with_value", "byte_and_with_value", "byte_xor_with_value", None, "byte_ramp_up", "byte_ramp_down", "byte_add_value", "byte_subtract_value", "byte_subtract_from", "byte_multiply_by", "byte_divide_by", "byte_divide_from", None, "byte_reverse_selection", "byte_reverse_group",],
    ["Jumpman", ["Edit Level", "jumpman_level_list"], None, "clear_trigger", "set_trigger", None, "add_assembly_source", "recompile_assembly_source"],
    ["Segments", ["View Segment", "segment_select"], None, "segment_from_selection", "segment_multiple_from_selection", "segment_interleave", "segment_origin", None, "segment_goto"],
    ["Help", "about"],
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
    }

    module_search_order = ["omnivore.viewers.actions", "omnivore_framework.actions", "omnivore.jumpman.actions"]

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
    def segment_number(self):
        return self.focused_viewer.linked_base.segment_number

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def can_copy(self):
        return self.focused_viewer.can_copy

    #### Initialization

    def __init__(self, action_factory_lookup=None):
        TileManagerBase.__init__(self, action_factory_lookup)
        self.center_base = None
        self.linked_bases = {}

    @classmethod
    def can_edit_file_exact(cls, file_metadata):
        return "atrcopy_parser" in file_metadata

    @classmethod
    def can_edit_file_generic(cls, file_metadata):
        mime_type = file_metadata['mime']
        return mime_type == "application/octet-stream"

    #### file handling

    def load(self, path, file_metadata, args=None):
        doc = self.document = DiskImageDocument()
        template_metadata = doc.get_document_template_metadata(file_metadata)
        self.load_extra_metadata(path, template_metadata)
        print("file_metadata", file_metadata)
        print("template_metadata", template_metadata)
        # print("extra_metadata", self.extra_metadata)
        print("args", args)

        if "atrcopy_parser" in file_metadata:
            doc.load_from_atrcopy_parser(file_metadata, self.extra_metadata)
        else:
            with fsopen(path, 'rb') as fh:
                data = fh.read()
            doc.load_from_raw_data(data, file_metadata, self.extra_metadata)

        if self.has_command_line_viewer_override(args):
            self.create_layout_from_args(args)
        else:
            self.restore_linked_bases()
            self.restore_layout_and_viewers()
            self.restore_view_segment_number()
        self.set_initial_focused_viewer()

        print("document", self.document)
        print("segments", self.document.segments)
        self.document.recalc_event()

    def create_layout_from_args(self, args):
        print(f"Creating layout from {args}")
        self.center_base = LinkedBase(self)
        self.linked_bases = {self.center_base.uuid:self.center_base}
        viewer_metadata = {}
        for name, value in args.items():
            viewer_metadata[name.strip()] = {}
        self.create_viewers(viewer_metadata)
        self.center_base.view_segment_number(0)

    def restore_linked_bases(self):
        linked_bases = {}
        for b in self.editor_metadata.get("linked bases", []):
            base = LinkedBase(editor=self)
            base.from_metadata_dict(b)
            linked_bases[base.uuid] = base
            log.debug("metadata: linked_base[%s]=%s" % (base.uuid, base))
        uuid = self.editor_metadata.get("center_base", None)
        try:
            self.center_base = linked_bases[uuid]
        except KeyError:
            self.center_base = LinkedBase(editor=self)
            linked_bases[self.center_base.uuid] = self.center_base

        log.critical(f"linked_bases: {linked_bases}")
        self.linked_bases = linked_bases

    def restore_view_segment_number(self):
        view_map = self.editor_metadata.get("linked_base_view_segment_number", {})
        for uuid, lb in self.linked_bases.items():
            segment_number = view_map.get(uuid, 0)
            print(f"restore_view_segment_number: {uuid}->{segment_number}")
            lb.view_segment_number(segment_number)


    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'diff highlight' in e:
            self.diff_highlight = bool(e['diff highlight'])

        viewers = e.get('viewers', [])
        log.debug("metadata: viewers=%s" % str(viewers))
        
        if not viewers:
            try:
                e_default = self.get_default_layout()
                print(("using defaults from template: template=%s" % str(e_default)))
            except OSError:
                log.error("No template for default layout; falling back to minimal setup.")
            else:
                e.update(e_default)
                viewers = e.get('viewers', [])
            log.debug("from layout: viewers=%s" % str(viewers))

        layout = e.get('layout', {})
        log.debug("metadata: layout=%s" % str(layout))

        viewer_metadata = {}
        for v in viewers:
            viewer_metadata[v['uuid']] = v
            log.debug("metadata: viewer[%s]=%s" % (v['uuid'], str(v)))

        log.debug("task arguments: '%s'" % self.task_arguments)
        if self.task_arguments or not viewer_metadata:
            names = self.task_arguments if self.task_arguments else self.default_viewers
            log.debug("overriding viewers: %s" % str(names))
            override_viewer_metadata = {}
            for viewer_name in names.split(","):
                if viewer_name == "emulator":
                    continue
                override_viewer_metadata[viewer_name.strip()] = {}
                log.debug("metadata: clearing viewer[%s] because specified in task args" % (viewer_name.strip()))
            if override_viewer_metadata:
                # found some specified viewers, so override the default layout
                viewer_metadata = override_viewer_metadata
                layout = {}  # empty layout so it isn't cluttered with unused windows

        linked_bases = {}
        for b in e.get('linked bases', []):
            base = LinkedBase(editor=self)
            base.from_metadata_dict(b)
            linked_bases[base.uuid] = base
            log.debug("metadata: linked_base[%s]=%s" % (base.uuid, base))
        uuid = e.get("center_base", None)
        try:
            self.center_base = linked_bases[uuid]
        except KeyError:
            self.center_base = LinkedBase(editor=self)
        self.create_viewers(layout, viewer_metadata, e, linked_bases)
        viewer = None
        if 'focused viewer' in e:
            u = e['focused viewer']
            viewer = self.find_viewer_by_uuid(u)
        self.task.segments_changed = self.document.segments

    def to_metadata_dict(self, mdict, document):
        self.prepare_metadata_for_save()
        mdict["diff highlight"] = self.diff_highlight
        mdict["layout"] = self.control.calc_layout()
        mdict["viewers"] = []
        bases = {}
        for v in self.viewers:
            b = v.linked_base
            bases[b.uuid] = b
            e = {"linked base": v.linked_base.uuid}
            v.to_metadata_dict(e, document)
            mdict["viewers"].append(e)
        if self.center_base is not None:
            bases[self.center_base.uuid] = self.center_base
            mdict["center_base"] = self.center_base.uuid
        else:
            mdict["center_base"] = None
        mdict["linked bases"] = []
        for u, b in bases.items():
            e = {}
            b.to_metadata_dict(e, document)
            mdict["linked bases"].append(e)
        mdict["focused viewer"] = self.focused_viewer.uuid
        # if document == self.document:
        #     # If we're saving the document currently displayed, save the
        #     # display parameters too.
        #     mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper

    def prepare_metadata_for_save(self):
        pass

    def rebuild_document_properties(self):
        if not self.document.has_baseline:
            self.use_self_as_baseline(self.document)
        FrameworkEditor.rebuild_document_properties(self)
        b = self.focused_viewer.linked_base
        if b.segment_number == 0:
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
    def clipboard_data_format(self):
        return self.focused_viewer.clipboard_data_format

    def copy_selection_to_clipboard(self, name):
        return clipboard.set_from_selection(self.focused_viewer, name)

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

    @property
    def supported_clipboard_data_objects(self):
        return self.focused_viewer.supported_clipboard_data_objects

    def select_all(self):
        self.focused_viewer.select_all()
        self.linked_base.refresh_event = True

    def select_none(self):
        self.focused_viewer.select_none()
        self.linked_base.refresh_event = True

    def select_invert(self):
        self.focused_viewer.select_invert()
        self.linked_base.refresh_event = True

    def check_document_change(self):
        self.document.change_count += 1
        self.update_caret_history()

    def rebuild_ui(self):
        log.debug("rebuilding focused_base: %s" % str(self.focused_viewer.linked_base))
        self.document.recalc_event = True

    def refresh_panes(self):
        log.debug("refresh_panes called")

    def reconfigure_panes(self):
        self.update_pane_names()

    def update_pane_names(self):
        for viewer in self.viewers:
            viewer.update_caption()
        self.control.update_captions()

    def view_segment_number(self, number):
        base = self.focused_viewer.linked_base
        base.view_segment_number(number)
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
                if s.pretty_name not in found:
                    search_order.append(s)
                    found.add(s.pretty_name)
        log.debug("search order: %s" % [s.pretty_name for s in search_order])
        return search_order

    def compare_to_baseline(self):
        if self.diff_highlight and self.document.has_baseline:
            self.document.update_baseline()

    def add_user_segment(self, segment, update=True):
        self.document.add_user_segment(segment)
        self.added_segment(segment, update)

    def added_segment(self, segment, update=True):
        if update:
            self.update_segments_ui()
        self.metadata_dirty = True

    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
        self.update_segments_ui()
        self.metadata_dirty = True

    def update_segments_ui(self):
        # Note: via profiling, it turns out that this is a very heavyweight
        # call, producing hundreds of thousands of trait notifier events. This
        # should only be called when the number of segments or document has
        # changed. If only the segment being viewed is changed, just set the
        # task.segment_selected trait
        log.debug("update_segments_ui costs a lot of time!!!!!!")
        if self.focused_viewer.linked_base.segment_parser is not None:
            self.segment_parser_label = self.focused_viewer.linked_base.segment_parser.menu_name
        else:
            self.segment_parser_label = "No parser"
        self.task.segments_changed = self.document.segments
        self.focused_viewer.linked_base.segment_selected_event = self.segment_number

    def find_in_user_segment(self, base_index):
        # FIXME: Profiling shows this as a big bottleneck when there are
        # comments. It inefficiently loops over segments, then the call to
        # get_index_from_base is super slow in atrcopy because of all the
        # calculations and dereferences needed to compute the index. That
        # probably needs to be cached.
        for s in self.document.user_segments:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        for s in self.document.segment_parser.segments[1:]:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        return None, None

    def do_popup(self, control, popup):
        # The popup event may happen on a control that isn't the focused
        # viewer, and the focused_viewer needs to point to that control for
        # actions to work in the correct viewer. The focus needs to be forced
        # to that control, we can't necessarily count on the ActivatePane call
        # to work before the popup.
        self.focused_viewer = control.segment_viewer
        ret = FrameworkEditor.do_popup(self, control, popup)
        wx.CallAfter(self.force_focus, control.segment_viewer)
        return ret

    def change_bytes(self, start, end, byte_values, pretty=None):
        """Convenience function to perform a ChangeBytesCommand
        """
        self.document.change_count += 1
        cmd = CoalescingChangeByteCommand(self.segment, start, end, byte_values)
        if pretty:
            cmd.pretty_name = pretty
        self.process_command(cmd)

    def process_flags(self, flags):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        log.debug("processing flags: %s" % str(flags))
        d = self.document
        visible_range = False

        #self.caret_handler.process_caret_flags(flags, d)

        if flags.message:
            self.task.status_bar.message = flags.message

        if flags.metadata_dirty:
            self.metadata_dirty = True

        control = flags.advance_caret_position_in_control
        if control:
            control.post_process_caret_flags(flags)

        if flags.data_model_changed:
            log.debug(f"process_flags: data_model_changed")
            d.data_model_changed_event(flags=flags)
            d.change_count += 1
            flags.rebuild_ui = True
        elif flags.byte_values_changed:
            log.debug(f"process_flags: byte_values_changed")
            d.change_count += 1
            d.byte_values_changed_event(flags=flags)
            flags.refresh_needed = True
        elif flags.byte_style_changed:
            log.debug(f"process_flags: byte_style_changed")
            d.change_count += 1
            d.byte_style_changed_event(flags=flags)
            flags.rebuild_ui = True
            flags.refresh_needed = True

        if flags.rebuild_ui:
            log.debug(f"process_flags: rebuild_ui")
            d.recalc_event(flags=flags)
        if flags.refresh_needed:
            log.debug(f"process_flags: refresh_needed")
            d.recalc_event(flags=flags)
