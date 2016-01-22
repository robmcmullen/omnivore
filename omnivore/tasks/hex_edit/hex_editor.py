# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
from omnivore.framework.document import Document
from grid_control import HexEditControl
from omnivore.utils.file_guess import FileMetadata
import omnivore.utils.wx.fonts as fonts
import omnivore.utils.colors as colors
from omnivore.utils.dis6502 import Atari800Disassembler
from omnivore.utils.binutil import known_segment_parsers, ATRSegmentParser, XexSegmentParser, DefaultSegment, AnticFontSegment
from omnivore.utils.searchutil import known_searchers

from commands import PasteCommand


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
    
    antic_font_data = Any
    
    antic_font = Any
    
    antic_font_mapping = Enum(0, 1)
    
    font_mode = Enum(2, 4, 5, 6, 7, 8, 9)
    
    map_width = Int
    
    playfield_colors = Any
    
    color_standard = Enum(0, 1)
    
    disassembler = Any
    
    segment = Any(None)
    
    highlight_color = Any((100, 200, 230))
    
    unfocused_cursor_color = Any((128, 128, 128))
    
    background_color = Any((255, 255, 255))
    
    match_background_color = Any((255, 255, 180))
    
    comment_background_color = Any((255, 180, 200))
    
    text_color = Any((0, 0, 0))
    
    empty_color = Any(None)
    
    text_font = Any(None)
    
    last_cursor_index = Int(0)
    
    last_anchor_start_index = Int(0)
    
    last_anchor_end_index = Int(0)

    #### Events ####

    changed = Event

    key_pressed = Event(KeyPressedEvent)
    
    # Class attributes (not traits)
    
    font_list = None
    
    searchers = known_searchers
    
    rect_select = False
    
    ##### Default traits
    
    def _disassembler_default(self):
        return Atari800Disassembler
    
    def _segment_default(self):
        return DefaultSegment()
    
    def _text_font_default(self):
        prefs = self.task.get_preferences()
        return prefs.text_font
    
    def _antic_font_data_default(self):
        return fonts.A8DefaultFont
    
    def _font_mode_default(self):
        return 2  # Antic mode 2, Graphics 0
    
    def _antic_font_mapping_default(self):
        return 1  # ATASCII
    
    def _map_width_default(self):
        return 8  # ATASCII
    
    def _playfield_colors_default(self):
        return colors.powerup_colors()
    
    def _color_standard_default(self):
        return 0  # NTSC

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def create(self, parent):
        self.control = self._create_control(parent)
        self.init_fonts(self.window.application)
        self.task.fonts_changed = self.font_list

    def init_extra_metadata(self, doc):
        """ Set up any pre-calculated segments based on the type or content of
        the just-loaded document.
        """
        e = doc.extra_metadata
        if 'colors' in e:
            self.update_colors(e['colors'])
        if 'font' in e:
            self.set_font(e['font'][0], e['font'][1])
        if 'initial segment' in e:
            self.initial_segment = e['initial segment']

    def rebuild_document_properties(self):
        self.find_segment()
    
    def copy_view_properties(self, old_editor):
        self.update_colors(old_editor.playfield_colors)
        self.set_font(old_editor.antic_font_data, old_editor.font_mode)
    
    def document_length(self):
        return len(self.segment)
    
    def process_paste_data_object(self, data_obj):
        bytes = self.get_numpy_from_data_object(data_obj)
        cmd = PasteCommand(self.segment, self.anchor_start_index, self.anchor_end_index, bytes)
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
        if wx.DF_TEXT in data_obj.GetAllFormats():
            value = data_obj.GetText().encode('utf-8')
        elif wx.DF_UNICODETEXT in data_obj.GetAllFormats():  # for windows
            value = data_obj.GetText().encode('utf-8')
        else:
            value = data_obj.GetData()
        bytes = np.fromstring(value, dtype=np.uint8)
        return bytes
    
    supported_clipboard_data_objects = [wx.CustomDataObject("numpy"), wx.TextDataObject()]
    
    def create_clipboard_data_object(self):
        if self.anchor_start_index != self.anchor_end_index:
            data = self.segment[self.anchor_start_index:self.anchor_end_index]
            data_obj = wx.CustomDataObject("numpy")
            data_obj.SetData(data.tostring())
            return data_obj
        return None
    
    def set_text_font(self, font, color):
        self.text_color = color
        self.text_font = font
        prefs = self.task.get_preferences()
        prefs.text_font = font

    def update_panes(self):
        self.segment = self.document.segments[self.segment_number]
        self.set_colors()
        self.reconfigure_panes()
        self.update_segments_ui()
    
    def update_segments_ui(self):
        self.segment_list.set_segments(self.document.segments, self.segment_number)
        self.task.segments_changed = self.document.segments
        self.task.segment_selected = self.segment_number
    
    def reconfigure_panes(self):
        self.control.recalc_view()
        self.disassembly.recalc_view()
        self.byte_graphics.recalc_view()
        self.font_map.recalc_view()
        self.memory_map.recalc_view()
    
    def check_document_change(self):
        if self.last_cursor_index != self.cursor_index or self.last_anchor_start_index != self.anchor_start_index or self.last_anchor_end_index != self.anchor_end_index:
            self.document.change_count += 1
    
    def refresh_panes(self):
        self.check_document_change()
        self.control.refresh_view()
        self.disassembly.refresh_view()
        self.byte_graphics.refresh_view()
        self.font_map.refresh_view()
        self.memory_map.refresh_view()
    
    def set_colors(self):
        if self.empty_color is None:
            attr = self.control.GetDefaultAttributes()
            self.empty_color = attr.colBg.Get(False)
    
    def update_colors(self, colors):
        if len(colors) == 5:
            self.playfield_colors = colors
        else:
            self.playfield_colors = colors[4:9]
        self.set_font()
        self.reconfigure_panes()
    
    def set_color_standard(self, std):
        self.color_standard = std
        self.update_colors(self.playfield_colors)
    
    def get_color_converter(self):
        if self.color_standard == 0:
            return colors.gtia_ntsc_to_rgb
        return colors.gtia_pal_to_rgb
    
    def update_fonts(self):
        self.font_map.Refresh()
        pane = self.window.get_dock_pane('hex_edit.font_map')
        pane.name = self.font_map.get_font_mapping_name()
        self.window._aui_manager.Update()
        
    @classmethod
    def init_fonts(cls, application):
        if cls.font_list is None:
            try:
                cls.font_list = application.get_bson_data("font_list")
            except IOError:
                # file not found
                cls.font_list = []
            except ValueError:
                # bad JSON format
                cls.font_list = []
    
    def remember_fonts(self):
        self.window.application.save_bson_data("font_list", self.font_list)
    
    def get_antic_font(self):
        color_converter = self.get_color_converter()
        return fonts.AnticFont(self.antic_font_data, self.font_mode, self.playfield_colors, self.highlight_color, self.match_background_color, self.comment_background_color, color_converter)
    
    def set_font(self, font=None, font_mode=None):
        if font is None:
            font = self.antic_font_data
        if font_mode is None:
            font_mode = self.font_mode
        self.font_mode = font_mode
        self.antic_font_data = font
        self.antic_font = self.get_antic_font()
        self.font_map.set_font()
        self.set_font_mapping()
    
    def set_font_mapping(self, font_mapping=None):
        if font_mapping is None:
            font_mapping = self.antic_font_mapping
        self.antic_font_mapping = font_mapping
        self.font_map.set_font_mapping(self.antic_font_mapping)
        self.update_fonts()
    
    def set_map_width(self, width=None):
        if width is None:
            width = self.map_width
        self.map_width = width
        self.font_map.recalc_view()
    
    def load_font(self, filename):
        try:
            fh = open(filename, 'rb')
            data = fh.read() + "\0"*1024
            data = data[0:1024]
            font = {
                'name': os.path.basename(filename),
                'data': data,
                'char_w': 8,
                'char_h': 8,
                }
            self.set_font(font)
            self.font_list.append(font)
            self.remember_fonts()
            self.task.fonts_changed = self.font_list
        except:
            raise
    
    def get_font_from_selection(self):
        pass
    
    def set_disassembler(self, disassembler):
        self.disassembler = disassembler
        self.disassembly.recalc_view()
    
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
        print new_segment
        self.view_segment_set_width(new_segment)
        self.select_none(refresh=False)
    
    def set_segment_parser(self, parser):
        self.find_segment_parser([parser])
        self.update_panes()
    
    def view_segment_set_width(self, segment):
        self.map_width = 8
    
    def view_segment_number(self, number):
        doc = self.document
        num = number if number < len(doc.segments) else 0
        if num != self.segment_number:
            new_segment = doc.segments[num]
            self.adjust_selection(self.segment, new_segment)
            self.segment = new_segment
            self.segment_number = num
            self.invalidate_search()
            self.update_segments_ui()
            self.view_segment_set_width(new_segment)
            self.reconfigure_panes()
            self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
    
    def invalidate_search(self):
        self.task.change_minibuffer_editor(self)
    
    def adjust_selection(self, current_segment, new_segment):
        """Adjust the selection of the current segment so that it is limited to the
        bounds of the new segment.
        
        If the current selection is entirely out of bounds of the new segment,
        all the selection indexes will be set to zero.
        """
        indexes = np.array([self.cursor_index, self.anchor_initial_start_index, self.anchor_start_index, self.anchor_initial_end_index, self.anchor_end_index], dtype=np.int64)
        
        # find byte index of view into master array
        current_offset = np.byte_bounds(current_segment.data)[0]
        new_offset = np.byte_bounds(new_segment.data)[0]
        
        delta = new_offset - current_offset
        indexes -= delta
        indexes.clip(0, len(new_segment) - 1, out=indexes)
        sel = indexes[1:5]
        same = (sel == sel[0])
        if same.all():
            indexes[1:5] = 0
        self.cursor_index, self.anchor_initial_start_index, self.anchor_start_index, self.anchor_initial_end_index, self.anchor_end_index = list(indexes)
    
    def get_segment_from_selection(self):
        data = self.segment[self.anchor_start_index:self.anchor_end_index]
        segment = DefaultSegment(self.segment.start_addr + self.anchor_start_index, data)
        return segment
    
    def add_user_segment(self, segment):
        self.document.add_user_segment(segment)
        self.update_segments_ui()
    
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
        self.antic_font = self.get_antic_font()

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.disassembly = self.window.get_dock_pane('hex_edit.disasmbly_pane').control
        self.byte_graphics = self.window.get_dock_pane('hex_edit.byte_graphics').control
        self.font_map = self.window.get_dock_pane('hex_edit.font_map').control
        self.memory_map = self.window.get_dock_pane('hex_edit.memory_map').control
        self.segment_list = self.window.get_dock_pane('hex_edit.segments').control
        self.undo_history = self.window.get_dock_pane('hex_edit.undo').control

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
        if control != self.byte_graphics:
            self.byte_graphics.select_index(index)
        if control != self.font_map:
            self.font_map.select_index(index)
        if control != self.memory_map:
            self.memory_map.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
