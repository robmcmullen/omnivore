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
from grid_control import HexEditControl
from omnivore.utils.file_guess import FileMetadata
from omnivore.arch.machine import Machine, Atari800
from omnivore.utils.segmentutil import known_segment_parsers, DefaultSegment, AnticFontSegment
from omnivore.utils.searchutil import known_searchers

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
        self.machine.init_fonts(self)
        self.machine.init_colors(self)
        self.task.fonts_changed = self.machine.font_list

    def init_extra_metadata(self, doc):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        e = doc.extra_metadata
        if 'colors' in e:
            self.machine.update_colors(e['colors'])
        if 'font' in e:
            self.machine.set_font(e['font'][0], e['font'][1])
        if 'initial segment' in e:
            self.initial_segment = e['initial segment']

    def rebuild_document_properties(self):
        self.find_segment()
    
    def copy_view_properties(self, old_editor):
        self.machine.update_colors(old_editor.machine.playfield_colors)
        self.machine.set_font(old_editor.machine.antic_font_data, old_editor.machine.font_renderer)
    
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
    
    supported_clipboard_data_objects = [wx.CustomDataObject("numpy,multiple"), wx.CustomDataObject("numpy"), wx.CustomDataObject("numpy,columns"), wx.TextDataObject()]
    
    def create_clipboard_data_object(self):
        ranges, indexes = self.get_selected_ranges_and_indexes()
        if len(ranges) == 1:
            r = ranges[0]
            data = self.segment[r[0]:r[1]]
            data_obj = wx.CustomDataObject("numpy")
            data_obj.SetData(data.tostring())
            return data_obj
        elif np.alen(indexes) > 0:
            data = self.segment[indexes]
            s1 = data.tostring()
            s2 = indexes.tostring()
            data_obj = wx.CustomDataObject("numpy,multiple")
            s = "%d,%s%s" % (len(s1), s1, s2)
            data_obj.SetData(s)
            return data_obj
        return None

    def update_panes(self):
        self.segment = self.document.segments[self.segment_number]
        self.reconfigure_panes()
        self.update_segments_ui()
    
    def update_segments_ui(self):
        self.segment_list.set_segments(self.document.segments, self.segment_number)
        self.task.segments_changed = self.document.segments
        self.task.segment_selected = self.segment_number
    
    def reconfigure_panes(self):
        self.control.recalc_view()
        self.disassembly.recalc_view()
        self.bitmap.recalc_view()
        self.font_map.recalc_view()
    
    def check_document_change(self):
        if self.last_cursor_index != self.cursor_index or self.last_anchor_start_index != self.anchor_start_index or self.last_anchor_end_index != self.anchor_end_index:
            self.document.change_count += 1
    
    def refresh_panes(self):
        self.check_document_change()
        self.control.refresh_view()
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
    
    @on_trait_change('machine.bitmap_change_event')
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
    
    def find_segment(self, segment_name=None):
        if segment_name is not None:
            index = self.document.find_segment_index_by_name(segment_name)
            if index < 0:
                index = 0
        else:
            index = 0
        self.segment_number = index
        self.segment_parser = self.document.segment_parser
        self.update_segments_ui()
        new_segment = self.document.segments[index]
        self.view_segment_set_width(new_segment)
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
            self.update_segments_ui()
            self.view_segment_set_width(self.segment)
            self.reconfigure_panes()
            self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
    
    def save_segment(self, saver, uri):
        try:
            bytes = saver.encode_data(self.segment)
            self.save_to_uri(bytes, uri)
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
    
    def invalidate_search(self):
        self.task.change_minibuffer_editor(self)
    
    def adjust_selection(self, old_segment):
        """Adjust the selection of the current segment so that it is limited to the
        bounds of the new segment.
        
        If the current selection is entirely out of bounds of the new segment,
        all the selection indexes will be set to zero.
        """
        # find byte index of view into master array
        g = self.document.global_segment
        s = self.segment
        global_offset = g.byte_bounds_offset()
        new_offset = s.byte_bounds_offset()
        old_offset = old_segment.byte_bounds_offset()
        
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
    
    def convert_ranges(self, from_style, to_style):
        s = self.segment
        ranges = s.get_style_ranges(**from_style)
        s.clear_style_bits(**from_style)
        s.clear_style_bits(**to_style)
        s.set_style_ranges(ranges, **to_style)
        self.selected_ranges = s.get_style_ranges(selected=True)
        self.document.change_count += 1
    
    def get_segment_from_selection(self):
        data = self.segment[self.anchor_start_index:self.anchor_end_index]
        style = self.segment.style[self.anchor_start_index:self.anchor_end_index]
        segment = DefaultSegment(data, style, self.segment.start_addr + self.anchor_start_index)
        return segment
    
    def add_user_segment(self, segment):
        self.document.add_user_segment(segment)
        self.update_segments_ui()
    
    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
    
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

    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        self.control = HexEditControl(parent, self.task)

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

        return self.control

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        self.cursor_index = index
        self.check_document_change()
        if control != self.control:
            self.control.select_index(index)
        if control != self.disassembly:
            self.disassembly.select_index(index)
        if control != self.bitmap:
            self.bitmap.select_index(index)
        if control != self.font_map:
            self.font_map.select_index(index)
        self.sidebar.refresh_active()
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
