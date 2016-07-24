# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
from omnivore.framework.document import Document
from omnivore.framework.actions import *
from grid_control import HexEditControl
from omnivore.utils.file_guess import FileMetadata
from omnivore.arch.machine import Machine, Atari800
from omnivore.utils.segmentutil import DefaultSegment, AnticFontSegment
from omnivore.utils.searchutil import known_searchers
from omnivore.utils.processutil import run_detach

from actions import *
from commands import PasteCommand

import logging
log = logging.getLogger(__name__)


class HexEditor(FrameworkEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """

    #### 'IPythonEditor' interface ############################################

    obj = Instance(File)

    #### traits
    
    grid_range_selected = Bool
    
    segment_parser = Any
    
    segment_number = Int(0)
    
    emulator_label = Unicode("Run Emulator")

    segment_parser_label = Unicode("<parser type>")
    
    ### View traits
    
    map_width = Int
    
    map_zoom = Int
    
    bitmap_width = Int
    
    bitmap_zoom = Int
    
    machine = Any
    
    segment = Any(None)
    
    last_cursor_index = Int(0)
    
    last_anchor_start_index = Int(0)
    
    last_anchor_end_index = Int(0)
    
    can_copy_baseline = Bool

    #### Events ####

    changed = Event

    key_pressed = Event(KeyPressedEvent)
    
    # Class attributes (not traits)
    
    searchers = known_searchers
    
    rect_select = False
    
    ##### Default traits
    
    def _machine_default(self):
        return Atari800
    
    def _segment_default(self):
        return DefaultSegment()
    
    def _map_width_default(self):
        prefs = self.task.get_preferences()
        return prefs.map_width
    
    def _map_zoom_default(self):
        return 2
    
    def _bitmap_width_default(self):
        prefs = self.task.get_preferences()
        return prefs.bitmap_width
    
    def _bitmap_zoom_default(self):
        return 5

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def create(self, parent):
        self.control = self._create_control(parent)
        self.machine.one_time_init(self)
        self.task.machine_menu_changed = self.machine

    def load_builtin_extra_metadata(self, doc):
        """ see if the document matches any hardcoded document information
        """
        from omnivore.utils.extra_metadata import check_builtin
        e = check_builtin(doc)
        if 'machine mime' not in e:
            e['machine mime'] = doc.metadata.mime
        return e

    def get_filesystem_extra_metadata_uri(self, doc):
        return doc.metadata.uri + ".omnivore"

    def process_extra_metadata(self, doc, e):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        if 'machine mime' in e:
            mime = e['machine mime']
            if not mime.startswith(self.machine.mime_prefix):
                m = self.machine.find_machine_by_mime(mime)
                if m is not None:
                    self.machine = m
        if 'user segments' in e:
            for s in e['user segments']:
                doc.add_user_segment(s, replace=True)
        first_segment = doc.segments[0]
        if 'serialized user segments' in e:
            for s in e['serialized user segments']:
                s.reconstruct_raw(first_segment.rawdata) 
                doc.add_user_segment(s, replace=True)
        first_segment.restore_extra_from_dict(e)
        if 'emulator' in e:
            doc.emulator = e['emulator']
        if 'colors' in e:
            self.machine.update_colors(e['colors'])
        if 'font' in e:
            # FIXME: I don't think 'font' is set anywhere, so this never gets called
            self.machine.set_font(e['font'][0], e['font'][1])
        if 'initial segment' in e:
            self.initial_segment = e['initial segment']
        if 'baseline document' in e:
            self.load_baseline(e['baseline document'], doc)
        if 'diff highlight' in e:
            self.diff_highlight = doc.has_baseline and bool(e['diff highlight'])
    
    def get_extra_metadata(self, mdict):
        mdict["serialized user segments"] = list(self.document.user_segments)
        base = self.document.segments[0]
        base.serialize_extra_to_dict(mdict)

        emu = self.document.emulator
        if emu and not 'system default' in emu:
            mdict["emulator"] = self.document.emulator
        if self.document.baseline_document is not None:
            mdict["baseline document"] = self.document.baseline_document.metadata.uri
            mdict["diff highlight"] = self.diff_highlight

    def rebuild_document_properties(self):
        FrameworkEditor.rebuild_document_properties(self)
        self.find_segment()
        self.update_emulator()
        self.compare_to_baseline()
        self.task.machine_menu_changed = self.machine
    
    def copy_view_properties(self, old_editor):
        try:
            self.machine = old_editor.machine.clone_machine()
        except AttributeError:
            self.machine = self._machine_default()
    
    @property
    def document_length(self):
        return len(self.segment)
    
    def process_paste_data_object(self, data_obj, cmd_cls=None):
        bytes, extra = self.get_numpy_from_data_object(data_obj)
        ranges, indexes = self.get_selected_ranges_and_indexes()
        if extra and extra[0] == "numpy,multiple":
            source_indexes = extra[1]
        else:
            source_indexes = None
        if cmd_cls is None:
            cmd_cls = PasteCommand
        cmd = cmd_cls(self.segment, ranges, self.cursor_index, bytes, source_indexes)
        self.process_command(cmd)
    
    def get_numpy_from_data_object(self, data_obj):
        # Full list of valid data formats:
        #
        # >>> import wx
        # >>> [x for x in dir(wx) if x.startswith("DF_")]
        # ['DF_BITMAP', 'DF_DIB', 'DF_DIF', 'DF_ENHMETAFILE', 'DF_FILENAME',
        # 'DF_HTML', 'DF_INVALID', 'DF_LOCALE', 'DF_MAX', 'DF_METAFILE',
        # 'DF_OEMTEXT', 'DF_PALETTE', 'DF_PENDATA', 'DF_PRIVATE', 'DF_RIFF',
        # 'DF_SYLK', 'DF_TEXT', 'DF_TIFF', 'DF_UNICODETEXT', 'DF_WAVE']
        extra = None
        if wx.DF_TEXT in data_obj.GetAllFormats():
            value = data_obj.GetText().encode('utf-8')
        elif wx.DF_UNICODETEXT in data_obj.GetAllFormats():  # for windows
            value = data_obj.GetText().encode('utf-8')
        else:
            value = data_obj.GetData()
            fmt = data_obj.GetPreferredFormat()
            if fmt.GetId() == "numpy,columns":
                r, c, value = value.split(",", 2)
                extra = fmt.GetId(), int(r), int(c)
            elif fmt.GetId() == "numpy,multiple":
                i, value = value.split(",", 1)
                i = int(i)
                value, index_string = value[0:i], value[i:]
                indexes = np.fromstring(index_string, dtype=np.uint32)
                extra = fmt.GetId(), indexes
        bytes = np.fromstring(value, dtype=np.uint8)
        return bytes, extra
    
    supported_clipboard_data_objects = [
        wx.CustomDataObject("numpy,multiple"),
        wx.CustomDataObject("numpy"),
        wx.CustomDataObject("numpy,columns"),
        wx.TextDataObject(),
        ]
    
    def create_clipboard_data_object(self):
        ranges, indexes = self.get_selected_ranges_and_indexes()
        if len(ranges) == 1:
            r = ranges[0]
            data = self.segment[r[0]:r[1]]
            data_obj = wx.CustomDataObject("numpy")
            data_obj.SetData(data.tostring())
        elif np.alen(indexes) > 0:
            data = self.segment[indexes]
            s1 = data.tostring()
            s2 = indexes.tostring()
            data_obj = wx.CustomDataObject("numpy,multiple")
            s = "%d,%s%s" % (len(s1), s1, s2)
            data_obj.SetData(s)
        else:
            data_obj = None
        if data_obj is not None:
            text = " ".join(["%02x" % i for i in data])
            text_obj = wx.TextDataObject()
            text_obj.SetText(text)
            c = wx.DataObjectComposite()
            c.Add(data_obj)
            c.Add(text_obj)
            return c
        return None

    def update_panes(self):
        self.segment = self.document.segments[self.segment_number]
        self.reconfigure_panes()
        self.update_segments_ui()
    
    def update_segments_ui(self):
        self.segment_list.set_segments(self.document.segments, self.segment_number)
        if self.segment_parser is not None:
            self.segment_parser_label = self.segment_parser.menu_name
        else:
            self.segment_parser_label = "No parser"
        self.task.segments_changed = self.document.segments
        self.task.segment_selected = self.segment_number
    
    def reconfigure_panes(self):
        self.hex_edit.recalc_view()
        self.disassembly.recalc_view()
        self.bitmap.recalc_view()
        self.font_map.recalc_view()
    
    def check_document_change(self):
        if self.last_cursor_index != self.cursor_index or self.last_anchor_start_index != self.anchor_start_index or self.last_anchor_end_index != self.anchor_end_index:
            self.document.change_count += 1
            self.update_cursor_history()

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
        print self.cursor_history
    
    def refresh_panes(self):
        self.check_document_change()
        self.hex_edit.refresh_view()
        self.disassembly.refresh_view()
        self.bitmap.refresh_view()
        self.font_map.refresh_view()
        self.sidebar.refresh_active()
    
    def set_bitmap_width(self, width=None):
        if width is None:
            width = self.bitmap_width
        self.bitmap_width = width
        self.bitmap.recalc_view()
    
    def set_bitmap_zoom(self, zoom=None):
        if zoom is None:
            zoom = self.bitmap_zoom
        self.bitmap_zoom = zoom
        self.bitmap.recalc_view()
    
    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self):
        self.bitmap.recalc_view()
    
    @on_trait_change('machine.font_change_event')
    def update_fonts(self):
        self.font_map.set_font()
        self.font_map.Refresh()
        pane = self.window.get_dock_pane('hex_edit.font_map')
        pane.name = self.machine.font_mapping.name
        self.window._aui_manager.Update()
    
    @on_trait_change('machine.disassembler_change_event')
    def update_disassembler(self):
        self.disassembly.recalc_view()
    
    @on_trait_change('document.emulator_change_event')
    def update_emulator(self):
        emu = self.document.emulator
        if emu is None:
            emu = self.machine.get_system_default_emulator(self.task)
        if not self.machine.is_known_emulator(emu):
            self.machine.add_emulator(self.task, emu)
        self.emulator_label = "Run using '%s'" % emu['name']

    def run_emulator(self):
        emu = self.document.emulator
        if not emu:
            emu = self.machine.get_system_default_emulator(self.task)
        if self.dirty:
            if not self.save():
                return
        exe = emu['exe']
        args = emu['args']
        fspath = self.document.filesystem_path()
        if fspath is not None:
            try:
                run_detach(exe, args, fspath, "%s")
            except RuntimeError, e:
                self.window.error("Failed launching %s %s\n\nError: %s" % (exe, args, str(e)), "%s Emulator Error" % emu['name'])
        else:
            self.window.error("Can't run emulator on:\n\n%s\n\nDocument is not on local filesystem" % self.document.uri, "%s Emulator Error" % emu['name'])

    def set_map_width(self, width=None):
        if width is None:
            width = self.map_width
        self.map_width = width
        self.font_map.recalc_view()
    
    def set_map_zoom(self, zoom=None):
        if zoom is None:
            zoom = self.map_zoom
        self.map_zoom = zoom
        self.font_map.recalc_view()
    
    def get_font_from_selection(self):
        pass
    
    def set_machine(self, machine):
        self.machine = machine
        self.reconfigure_panes()
    
    def find_segment_parser(self, parsers, segment_name=None):
        self.document.parse_segments(parsers)
        self.find_segment(segment_name)

    def find_first_valid_segment_index(self):
        return 0
    
    def find_segment(self, segment_name=None, segment=None):
        if segment_name is not None:
            index = self.document.find_segment_index_by_name(segment_name)
        elif segment is not None:
            index = self.document.find_segment_index(segment)
        else:
            index = self.find_first_valid_segment_index()
        if index < 0:
            index = 0
        self.segment_number = index
        self.segment_parser = self.document.segment_parser
        self.update_segments_ui()
        self.segment = self.document.segments[index]
        self.view_segment_set_width(self.segment)
        self.select_none(refresh=False)
    
    def set_segment_parser(self, parser):
        self.find_segment_parser([parser])
        self.update_panes()
    
    def view_segment_set_width(self, segment):
        pass
    
    def view_segment_number(self, number):
        doc = self.document
        num = number if number < len(doc.segments) else len(doc.segments) - 1
        if num != self.segment_number:
            old_segment = self.segment
            self.segment = doc.segments[num]
            self.adjust_selection(old_segment)
            self.segment_number = num
            self.invalidate_search()
            self.view_segment_set_width(self.segment)
            self.reconfigure_panes()
            self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
        self.update_segments_ui()
    
    def get_extra_segment_savers(self, segment):
        savers = []
        savers.append(self.disassembly)
        return savers
    
    def save_segment(self, saver, uri):
        try:
            bytes = saver.encode_data(self.segment)
            self.save_to_uri(bytes, uri, save_metadata=False)
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            #self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            raise
    
    def invalidate_search(self):
        self.task.change_minibuffer_editor(self)
    
    def compare_to_baseline(self):
        if self.diff_highlight:
            self.document.update_baseline()
    
    def adjust_selection(self, old_segment):
        """Adjust the selection of the current segment so that it is limited to the
        bounds of the new segment.
        
        If the current selection is entirely out of bounds of the new segment,
        all the selection indexes will be set to zero.
        """
        # find byte index of view into master array
        g = self.document.global_segment
        s = self.segment
        global_offset = g.get_raw_index(0)
        new_offset = s.get_raw_index(0)
        old_offset = old_segment.get_raw_index(0)
        
        self.cursor_index -= new_offset - old_offset
        self.selected_ranges = s.get_style_ranges(selected=True)
        if self.selected_ranges:
            # Arbitrarily puth the anchor on the last selected range
            last = self.selected_ranges[-1]
            self.anchor_initial_start_index = self.anchor_start_index = last[0]
            self.anchor_initial_end_index = self.anchor_end_index = last[1]
        g.clear_style_bits(selected=True)
        self.document.change_count += 1
        self.highlight_selected_ranges()
    
    def highlight_selected_ranges(self):
        s = self.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges(self.selected_ranges, selected=True)
        self.document.change_count += 1
        self.can_copy_baseline = self.can_copy and self.baseline_present
    
    def convert_ranges(self, from_style, to_style):
        s = self.segment
        ranges = s.get_style_ranges(**from_style)
        s.clear_style_bits(**from_style)
        s.clear_style_bits(**to_style)
        s.set_style_ranges(ranges, **to_style)
        self.selected_ranges = s.get_style_ranges(selected=True)
        self.document.change_count += 1
    
    def get_label_at_index(self, index):
        return self.hex_edit.table.get_label_at_index(index)
    
    def get_label_of_ranges(self, ranges):
        labels = []
        for start, end in ranges:
            labels.append("%s-%s" % (self.get_label_at_index(start), self.get_label_at_index(end)))
        return ", ".join(labels)
    
    def get_segments_from_selection(self, size=-1):
        s = self.segment
        segments = []
        
        # Get the selected ranges directly from the segment style data, because
        # the individual range entries in self.selected_ranges can be out of
        # order or overlapping
        ranges = s.get_style_ranges(selected=True)
        if len(ranges) == 1:
            seg_start, seg_end = ranges[0]
            segment = DefaultSegment(s.rawdata[seg_start:seg_end], s.start_addr + seg_start)
            segments.append(segment)
        elif len(ranges) > 1:
            # If there are multiple selections, use an indexed segment
            indexes = []
            for start, end in ranges:
                indexes.extend(range(start, end))
            raw = s.rawdata.get_indexed(indexes)
            segment = DefaultSegment(raw, s.start_addr + indexes[0])
            segments.append(segment)
        return segments
    
    def get_selected_status_message(self):
        if not self.selected_ranges:
            return ""
        if len(self.selected_ranges) == 1:
            r = self.selected_ranges
            return "[%d bytes selected %s]" % (r[0][1] - r[0][0], self.get_label_of_ranges(r))
        else:
            return "[%d ranges selected]" % (len(self.selected_ranges))
    
    def show_status_message(self, msg):
        s = self.get_selected_status_message()
        if s:
            msg = "%s %s" % (s, msg)
        self.task.status_bar.message = msg
    
    def add_user_segment(self, segment, update=True):
        self.document.add_user_segment(segment)
        if update:
            self.update_segments_ui()
            self.segment_list.ensure_visible(segment)
        self.metadata_dirty = True
    
    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
        self.metadata_dirty = True
    
    def find_in_user_segment(self, base_index):
        for s in self.document.user_segments:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        return None, None
    
    def ensure_visible(self, start, end):
        self.index_clicked(start, 0, None)
    
    def update_history(self):
#        history = document.undo_stack.serialize()
#        self.window.application.save_log(str(history), "command_log", ".log")
        self.undo_history.update_history()

    def mark_index_range_changed(self, index_range):
        self.disassembly.restart_disassembly(index_range[0])
    
    def perform_idle(self):
        self.disassembly.perform_idle()
    
    def common_popup_actions(self):
        return [CutAction, CopyAction, CopyDisassemblyAction, CopyAsReprAction, PasteAction, None, SelectAllAction, SelectNoneAction, GetSegmentFromSelectionAction, None, MarkSelectionAsCodeAction, MarkSelectionAsDataAction, MarkSelectionAsDisplayListAction, MarkSelectionAsJumpmanLevelAction, MarkSelectionAsJumpmanHarvestAction, RevertToBaselineAction, None, AddCommentPopupAction, RemoveCommentPopupAction]
    
    def change_bytes(self, start, end, bytes, pretty=None):
        """Convenience function to perform a ChangeBytesCommand
        """
        print "changing bytes %d-%d to %s" % (start, end, repr(bytes))
        self.document.change_count += 1
        cmd = CoalescingChangeByteCommand(self.segment, start, end, bytes)
        if pretty:
            cmd.pretty_name = pretty
        self.process_command(cmd)

    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.hex_edit = HexEditControl(parent, self.task)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.disassembly = self.window.get_dock_pane('hex_edit.disassembly').control
        self.bitmap = self.window.get_dock_pane('hex_edit.bitmap').control
        self.font_map = self.window.get_dock_pane('hex_edit.font_map').control
        self.segment_list = self.window.get_dock_pane('hex_edit.segments').control
        self.undo_history = self.window.get_dock_pane('hex_edit.undo').control
        self.sidebar = self.window.get_dock_pane('hex_edit.sidebar')

        # Load the editor's contents.
        self.load()

        return self.hex_edit

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        self.check_document_change()
        if control != self.hex_edit:
            self.hex_edit.select_index(index)
        if control != self.disassembly:
            self.disassembly.select_index(index)
        if control != self.bitmap:
            self.bitmap.select_index(index)
        if control != self.font_map:
            self.font_map.select_index(index)
        self.sidebar.refresh_active()
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
        self.can_copy_baseline = self.can_copy and self.baseline_present
