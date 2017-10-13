# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json
from udis.udis_fast import TraceInfo, flag_origin

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change, HasTraits, Undefined
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
from omnivore.utils.command import DisplayFlags
from omnivore8bit.arch.machine import Machine, Atari800
from omnivore8bit.utils.segmentutil import SegmentData, DefaultSegment
from omnivore8bit.arch.disasm import iter_disasm_styles

import logging
log = logging.getLogger(__name__)


class LinkedBase(HasTraits):
    """Model for the state of a set of viewers. A ByteEditor can have an
    arbitrary number of LinkedBases, but all viewers that point to a common
    LinkedBase will all show the same data.

    A LinkedBase is tied to a Segment, and any data that can be applied
    segment-wide should also live here, e.g. the disassembly trace.

    Currently, a LinkedBase contains a single Machine, which specifies how to
    look at the data, like: CPU used for disassembly/assembly, available
    graphics and text modes, current colors and font. All views of the data
    using this LinkedBase will show the same Machine.

    In the future, each view will have its own Machine, because there's nothing
    in the Machine that could affect other viewers, so it should really be part
    of the view.
    """

    #### Traits

    # 

    obj = Instance(File)

    editor = Instance(FrameworkEditor)

    machine = Instance(Machine)

    segment = Instance(DefaultSegment)

    segment_number = Int(0)

    trace = Instance(TraceInfo)

    disassembler_cache = Dict

    last_cursor_index = Int(0)

    last_anchor_start_index = Int(0)

    last_anchor_end_index = Int(0)

    has_origin = Bool(False)

    segment_view_params = Dict

    # This is a flag to help set the cursor to the center row when the cursor
    # is moved in a different editor. Some editors can't use SetFocus inside an
    # event handler, so the focus could still be set on one editor even though
    # the user clicked on another. This results in the first editor not getting
    # centered unless this flag is checked also.
    pending_focus = Any(None)  # Flag to help

    #### Events

    recalc_event = Event

    ensure_visible_index = Event

    update_trace = Event

    update_cursor = Event

    disassembly_refresh_event = Event

    key_pressed = Event(KeyPressedEvent)

    #### Class attributes (not traits)

    rect_select = False

    #### Default traits

    def _machine_default(self):
        return Atari800

    def _segment_default(self):
        rawdata = SegmentData([])
        return DefaultSegment(rawdata)

    def _trace_default(self):
        return TraceInfo()

    #### Properties

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def hex_format_character(self):
        return "x" if self.editor.task.hex_grid_lower_case else "X"

    @property
    def task(self):
        return self.editor.task

    @property
    def window(self):
        return self.editor.window

    @property
    def document(self):
        return self.editor.document

    #### Convenience functions

    def __str__(self):
        return "LinkedBase: seg=%s" % self.segment

    def from_metadata_dict(self, e):
        if 'machine mime' in e:
            mime = e['machine mime']
            if not mime.startswith(self.machine.mime_prefix):
                m = self.machine.find_machine_by_mime(mime)
                if m is not None:
                    self.machine = m
        if 'font' in e:
            # FIXME: I don't think 'font' is set anywhere, so this never gets called
            self.machine.set_font(e['font'][0], e['font'][1])
        if 'initial segment' in e:
            self.initial_segment = e['initial segment']
        if 'diff highlight' in e:
            self.diff_highlight = bool(e['diff highlight'])
        if 'segment view params' in e:
            self.segment_view_params = e['segment view params']
        self.machine.restore_extra_from_dict(e)

    def to_metadata_dict(self, mdict, document):
        mdict["diff highlight"] = self.diff_highlight
        if document == self.document:
            # If we're saving the document currently displayed, save the
            # display parameters too.
            mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper
        self.machine.serialize_extra_to_dict(mdict)

    def rebuild_ui(self):
        self.segment = self.document.segments[self.segment_number]
        self.reconfigure_panes()
        self.update_segments_ui()

    def get_cursor_state(self):
        return self.segment, self.cursor_index

    def restore_cursor_state(self, state):
        segment, index = state
        number = self.document.find_segment_index(segment)
        if number < 0:
            log.error("tried to restore cursor to a deleted segment? %s" % segment)
        else:
            if number != self.segment_number:
                self.view_segment_number(number)
            self.index_clicked(index, 0, None)
        log.debug(self.cursor_history)

    def set_machine(self, machine):
        self.machine = machine
        self.reconfigure_panes()

    def save_segment_view_params(self, segment):
        d = {
            'cursor_index': self.editor.cursor_index,
        }
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    d[viewer.pane_info.name] = viewer.control.get_view_params()
                except AttributeError:
                    pass

        self.segment_view_params[segment.uuid] = d

    def restore_segment_view_params(self, segment):
        try:
            d = self.segment_view_params[segment.uuid]
        except KeyError:
            log.debug("no view params for %s" % segment.uuid)
            return
        log.debug("restoring view params for %s" % segment.uuid)
        self.editor.cursor_index = d['cursor_index']
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    params = d[viewer.pane_info.name]
                except KeyError:
                    continue
                try:
                    viewer.control.restore_view_params(params)
                except AttributeError:
                    continue

    def find_segment_parser(self, parsers, segment_name=None):
        self.document.parse_segments(parsers)
        self.find_segment(segment_name)

    def find_first_valid_segment_index(self):
        return 0

    def find_segment(self, segment_name=None, segment=None, refresh=False):
        if segment_name is not None:
            index = self.document.find_segment_index_by_name(segment_name)
        elif segment is not None:
            index = self.document.find_segment_index(segment)
        else:
            index = self.find_first_valid_segment_index()
        if index < 0:
            index = 0
        self.segment_parser = self.document.segment_parser
        if refresh:
            self.view_segment_number(index)
        else:
            self.segment_number = index
            self.segment_parser = self.document.segment_parser
            self.segment = self.document.segments[index]
            self.editor.select_none(refresh=False)
            self.restart_disassembly()
            self.task.segments_changed = self.document.segments
            self.task.segment_selected = self.segment_number

    def set_segment_parser(self, parser):
        self.find_segment_parser([parser])
        self.rebuild_ui()

    def view_segment_number(self, number):
        log.debug("view_segment_number: changing to %d from %d" % (number, self.segment_number))
        doc = self.document
        num = number if number < len(doc.segments) else len(doc.segments) - 1
        if num != self.segment_number:
            old_segment = self.segment
            if old_segment is not None:
                self.save_segment_view_params(old_segment)
            self.segment = doc.segments[num]
            self.adjust_selection(old_segment)
            self.segment_number = num

            self.force_data_model_update()

            #self.show_trace()
            # if self.segment_list is not None:
            #     self.segment_list.SetSelection(self.segment_number)
            # else:
            #     self.sidebar.refresh_active()
            self.editor.sidebar.refresh_active()
            self.task.segment_selected = self.segment_number
            #self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
            self.task.update_window_title()

    def force_data_model_update(self):
            self.disassembler_cache = {}  # force disassembler to use new segment
            flags = DisplayFlags()
            flags.data_model_changed = True
            self.editor.process_flags(flags)

    def save_segment(self, saver, uri):
        try:
            bytes = saver.encode_data(self.segment, self)
            saver = lambda a,b: bytes
            self.document.save_to_uri(uri, self, saver, save_metadata=False)
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            #self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            raise

    def adjust_selection(self, old_segment):
        """Adjust the selection of the current segment so that it is limited to the
        bounds of the new segment.
        
        If the current selection is entirely out of bounds of the new segment,
        all the selection indexes will be set to zero.
        """
        # find byte index of view into master array
        g = self.document.container_segment
        s = self.segment
        global_offset = g.get_raw_index(0)
        new_offset = s.get_raw_index(0)
        old_offset = old_segment.get_raw_index(0)

        self.restore_segment_view_params(s)
        self.selected_ranges = s.get_style_ranges(selected=True)
        if self.selected_ranges:
            # Arbitrarily puth the anchor on the last selected range
            last = self.selected_ranges[-1]
            self.anchor_initial_start_index = self.anchor_start_index = last[0]
            self.anchor_initial_end_index = self.anchor_end_index = last[1]
        g.clear_style_bits(selected=True)
        self.document.change_count += 1
        self.editor.highlight_selected_ranges()

    def convert_ranges(self, from_style, to_style):
        s = self.segment
        ranges = s.get_style_ranges(**from_style)
        s.clear_style_bits(**from_style)
        s.clear_style_bits(**to_style)
        s.set_style_ranges(ranges, **to_style)
        self.selected_ranges = s.get_style_ranges(selected=True)
        self.document.change_count += 1

    def get_segments_from_selection(self, size=-1):
        s = self.segment
        segments = []

        # Get the selected ranges directly from the segment style data, because
        # the individual range entries in self.selected_ranges can be out of
        # order or overlapping
        ranges = s.get_style_ranges(selected=True)
        if len(ranges) == 1:
            seg_start, seg_end = ranges[0]
            if size < 0:
                size = seg_end - seg_start
            for start in range(seg_start, seg_end, size):
                end = min(seg_end, start + size)
                segment = DefaultSegment(s.rawdata[start:end], s.start_addr + start)
                segments.append(segment)
        elif len(ranges) > 1:
            # If there are multiple selections, use an indexed segment
            indexes = []
            for start, end in ranges:
                indexes.extend(range(start, end))
            if size < 0:
                size = len(indexes)
            for i in range(0, len(indexes), size):
                raw = s.rawdata.get_indexed(indexes[i:i + size])
                segment = DefaultSegment(raw, s.start_addr + indexes[i])
                segments.append(segment)
        return segments

    def get_selected_status_message(self):
        if not self.editor.selected_ranges:
            return ""
        if len(self.editor.selected_ranges) == 1:
            r = self.editor.selected_ranges
            first = r[0][0]
            last = r[0][1]
            num = abs(last - first)
            if num == 1: # python style, 4:5 indicates a single byte
                return "[1 byte selected %s]" % self.editor.get_label_of_ranges(r)
            elif num > 0:
                return "[%d bytes selected %s]" % (num, self.editor.get_label_of_ranges(r))
        else:
            return "[%d ranges selected]" % (len(self.editor.selected_ranges))

    def show_status_message(self, msg):
        s = self.get_selected_status_message()
        if s:
            msg = "%s %s" % (msg, s)
        self.editor.task.status_bar.message = msg

    def add_user_segment(self, segment, update=True):
        self.document.add_user_segment(segment)
        self.added_segment(segment, update)

    def added_segment(self, segment, update=True):
        if update:
            self.update_segments_ui()
            if self.segment_list is not None:
                self.segment_list.ensure_visible(segment)
        self.metadata_dirty = True

    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
        self.update_segments_ui()
        self.metadata_dirty = True

    def find_in_user_segment(self, base_index):
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

    def ensure_visible(self, start, end):
        self.index_clicked(start, 0, None)

    def get_goto_action_in_segment(self, addr_dest):
        if addr_dest >= 0:
            segment_start = self.segment.start_addr
            segment_num = -1
            addr_index = addr_dest - segment_start
            segments = self.document.find_segments_in_range(addr_dest)
            if addr_dest < segment_start or addr_dest > segment_start + len(self.segment):
                # segment_num, segment_dest, addr_index = self.document.find_segment_in_range(addr_dest)
                if not segments:
                    msg = "Address $%04x not in any segment" % addr_dest
                    addr_dest = -1
                else:
                    # Don't chose a default segment, just show the sub menu
                    msg = None
            else:
                msg = "Go to $%04x" % addr_dest
            if msg:
                action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
            else:
                action = None
        else:
            msg = "No address to jump to"
            action = GotoIndexAction(name=msg, enabled=False, task=self.editor.task)
        return action

    def get_goto_actions_other_segments(self, addr_dest):
        """Add sub-menu to popup list for segments that have the same address
        """
        goto_actions = []
        segments = self.document.find_segments_in_range(addr_dest)
        if len(segments) > 0:
            other_segment_actions = ["Go to $%04x in Other Segment..." % addr_dest]
            for segment_num, segment_dest, addr_index in segments:
                if segment_dest == self.segment:
                    continue
                msg = str(segment_dest)
                action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
                other_segment_actions.append(action)
            if len(other_segment_actions) > 1:
                # found another segment other than itself
                goto_actions.append(other_segment_actions)
        return goto_actions

    def get_goto_actions_same_byte(self, index):
        """Add sub-menu to popup list for for segments that have the same raw
        index (index into the base array) as the index into the current segment
        """
        goto_actions = []
        raw_index = self.segment.get_raw_index(index)
        segments = self.document.find_segments_with_raw_index(raw_index)
        if len(segments) > 0:
            other_segment_actions = ["Go to Same Byte in Other Segment..."]
            for segment_num, segment_dest, addr_index in segments:
                if segment_dest == self.segment:
                    continue
                msg = str(segment_dest)
                action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
                other_segment_actions.append(action)
            if len(other_segment_actions) > 1:
                # found another segment other than itself
                goto_actions.append(other_segment_actions)
        return goto_actions

    def common_popup_actions(self):
        return [CutAction, CopyAction, ["Copy Special", CopyDisassemblyAction, CopyCommentsAction, CopyAsReprAction, CopyAsCBytesAction], PasteAction, ["Paste Special", PasteAndRepeatAction, PasteCommentsAction], None, SelectAllAction, SelectNoneAction, ["Mark Selection As", MarkSelectionAsCodeAction, MarkSelectionAsDataAction, MarkSelectionAsUninitializedDataAction, MarkSelectionAsDisplayListAction, MarkSelectionAsJumpmanLevelAction, MarkSelectionAsJumpmanHarvestAction], None, GetSegmentFromSelectionAction, RevertToBaselineAction, None, AddCommentPopupAction, RemoveCommentPopupAction, AddLabelPopupAction, RemoveLabelPopupAction]

    def change_bytes(self, start, end, bytes, pretty=None):
        """Convenience function to perform a ChangeBytesCommand
        """
        self.document.change_count += 1
        cmd = CoalescingChangeByteCommand(self.segment, start, end, bytes)
        if pretty:
            cmd.pretty_name = pretty
        self.process_command(cmd)

    def popup_visible(self):
        log.debug("checking sidebar: popup visible? %s" % self.sidebar.control.has_popup())
        return self.sidebar.control.has_popup()

    def clear_popup(self):
        log.debug("clearing popup")
        self.sidebar.control.clear_popup()

    #### Disassembler

    def get_current_disassembly(self, machine=None):
        if machine is None:
            machine = self.machine
        d = self.disassembler_cache.get(machine.disassembler.name, None)
        if d is None:
            log.debug("creating disassembler for %s" % machine.disassembler.name)
            d = machine.get_disassembler(self.task.hex_grid_lower_case, self.task.assembly_lower_case, self.document.document_memory_map, self.segment.memory_map)
            for i, name in iter_disasm_styles():
                d.add_chunk_processor(name, i)
            d.disassemble_segment(self.segment)
            self.disassembler_cache[machine.disassembler.name] = d
        log.debug("get_current_disassembly: %s" % str(d.info))
        return d

    def clear_disassembly(self, machine):
        log.debug("clear_disassembly")
        try:
            self.disassembler_cache.pop(machine.disassembler.name)
        except KeyError:
            pass

    def disassemble_segment(self, machine=None):
        log.debug("disassemble_segment")
        return self.get_current_disassembly(machine)

    def restart_disassembly(self, index_range=None):
        #start = index_range[0] if index_range is not None else 0
        log.debug("restart_disassembly")
        self.disassembler_cache = {}
        d = self.disassemble_segment()
        self.disassembly_refresh_event = True

    #### Disassembly tracing

    def start_trace(self):
        self.trace_info = TraceInfo()
        self.update_trace_in_segment()

    def get_trace(self, save=False):
        if save:
            kwargs = {'user': True}
        else:
            kwargs = {'match': True}
        s = self.segment
        mask = s.get_style_mask(**kwargs)
        style = s.get_style_bits(**kwargs)
        is_data = self.trace_info.marked_as_data
        size = min(len(is_data), len(s))
        trace = is_data[s.start_addr:s.start_addr + size] * style
        if save:
            # don't change data flags for stuff that's already marked as data
            s = self.segment
            already_data = np.logical_and(s.style[0:size] & user_bit_mask > 0, trace > 0)
            indexes = np.where(already_data)[0]
            previous = s.style[indexes]
            trace[indexes] = previous
        return trace, mask

    def update_trace_in_segment(self, save=False):
        trace, mask = self.get_trace(save)
        s = self.segment
        size = len(trace)
        s.style[0:size] &= mask
        s.style[0:size] |= trace

    def trace_disassembly(self, pc):
        self.disassembler.fast.trace_disassembly(self.table.trace_info, [pc])
        self.update_trace_in_segment()

    #### Trait event handling

    @on_trait_change('editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.restart_disassembly(index_range)

    @on_trait_change('editor.document.byte_style_changed')
    def byte_style_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.restart_disassembly(index_range)
