import os

# Major package imports.
import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Any, Bool, Int, Str, List, Dict, Event, Enum

# Local imports.
import fonts
import colors
from dis6502 import Basic6502Disassembler, Undocumented6502Disassembler, Flagged6502Disassembler
import machine_atari800
import machine_atari5200
import antic_renderers

class Machine(HasTraits):
    """ Collection of classes that identify a machine: processor, display, etc.
    
    """
    
    # Traits
    
    name = Str
    
    disassembler = Any
    
    memory_map = Dict
    
    antic_font_data = Any
    
    antic_font = Any
    
    playfield_colors = Any
    
    color_standard = Enum(0, 1)
    
    bitmap_renderer = Any
    
    font_renderer = Any
    
    font_mapping = Any
    
    # Trait events
    
    font_change_event = Event
    
    # Class attributes (not traits)
    
    font_list = None
    
    highlight_color = (100, 200, 230)
    
    unfocused_cursor_color = (128, 128, 128)
    
    background_color = (255, 255, 255)
    
    match_background_color = (255, 255, 180)
    
    comment_background_color = (255, 180, 200)
    
    empty_color = None
    
    text_color = (0, 0, 0)
    
    text_font = None
        
    @classmethod
    def init_fonts(cls, editor):
        if cls.font_list is None:
            try:
                cls.font_list = editor.window.application.get_bson_data("font_list")
            except IOError:
                # file not found
                cls.font_list = []
            except ValueError:
                # bad JSON format
                cls.font_list = []
        prefs = editor.task.get_preferences()
        cls.text_font = prefs.text_font
    
    @classmethod
    def remember_fonts(cls, application):
        application.save_bson_data("font_list", cls.font_list)
    
    @classmethod
    def init_colors(cls, editor):
        if cls.empty_color is None:
            attr = editor.control.GetDefaultAttributes()
            cls.empty_color = attr.colBg.Get(False)
    
    @classmethod
    def set_text_font(cls, editor, font, color):
        cls.text_color = color
        cls.text_font = font
        prefs = editor.task.get_preferences()
        prefs.text_font = font
    
    # Trait initializers
    
    def _name_default(self):
        return "Generic 6502"
    
    def _disassembler_default(self):
        return Basic6502Disassembler

    def _memory_map_default(self):
        return {}
    
    def _antic_font_default(self):
        return self.get_antic_font()
    
    def _antic_font_data_default(self):
        return fonts.A8DefaultFont
    
    def _playfield_colors_default(self):
        return colors.powerup_colors()
    
    def _color_standard_default(self):
        return 0  # NTSC
    
    def _bitmap_renderer_default(self):
        return antic_renderers.ModeF(self)
    
    def _font_renderer_default(self):
        return predefined_font_renderers[1]
    
    def _font_mapping_default(self):
        return predefined_font_mappings[1]
    
    # 
    
    def __eq__(self, other):
        return self.disassembler == other.disassembler and self.memory_map == other.memory_map

    def clone_machine(self):
        return self.clone_traits()
    
    #
    
    def update_colors(self, colors):
        if len(colors) == 5:
            self.playfield_colors = colors
        else:
            self.playfield_colors = colors[4:9]
        self.set_font()
    
    def get_color_converter(self):
        if self.color_standard == 0:
            return colors.gtia_ntsc_to_rgb
        return colors.gtia_pal_to_rgb
    
    def set_color_standard(self, std):
        self.color_standard = std
        self.update_colors(self.playfield_colors)
    
    def set_font(self, font=None, font_renderer=None):
        if font is None:
            font = self.antic_font_data
        if font_renderer is not None:
            self.font_renderer = font_renderer
        self.antic_font_data = font
        self.antic_font = self.get_antic_font()
        self.set_font_mapping()
    
    def set_font_mapping(self, font_mapping=None):
        if font_mapping is None:
            font_mapping = self.font_mapping
        self.font_mapping = font_mapping
        self.font_change_event = True
    
    def get_antic_font(self):
        color_converter = self.get_color_converter()
        return fonts.AnticFont(self.antic_font_data, self.font_renderer.font_mode, self.playfield_colors, self.highlight_color, self.match_background_color, self.comment_background_color, color_converter)
    
    def load_font(self, task, filename):
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
            self.remember_fonts(task.application)
            task.fonts_changed = self.font_list
        except:
            raise
    
    
    
    
    # Utility methods
    
    def get_disassembler(self, hex_lower, mnemonic_lower):
        return self.disassembler(self.memory_map, hex_lower, mnemonic_lower)


Generic6502 = Machine(name="Generic 6502", disassembler=Basic6502Disassembler)

Atari800 = Machine(name="Atari 800", disassembler=Basic6502Disassembler, memory_map=machine_atari800.memmap)

Atari800Undoc = Machine(name="Atari 800 (show undocumented opcodes)", disassembler=Undocumented6502Disassembler, memory_map=machine_atari800.memmap)

Atari800Flagged = Machine(name="Atari 800 (highlight undocumented opcodes)", disassembler=Flagged6502Disassembler, memory_map=machine_atari800.memmap)

Atari5200 = Machine(name="Atari 5200", disassembler=Basic6502Disassembler, memory_map=machine_atari5200.memmap)

predefined_machines = [
    Generic6502,
    Atari800,
    Atari800Undoc,
    Atari800Flagged,
    Atari5200,
    ]

predefined_disassemblers = [
    Basic6502Disassembler,
    Undocumented6502Disassembler,
    ]

predefined_font_renderers = [
    antic_renderers.Mode2(),
    antic_renderers.Mode4(),
    antic_renderers.Mode5(),
    antic_renderers.Mode6Upper(),
    antic_renderers.Mode6Lower(),
    antic_renderers.Mode7Upper(),
    antic_renderers.Mode7Lower(),
    ]

predefined_font_mappings = [
    antic_renderers.ATASCIIFontMapping(),
    antic_renderers.AnticFontMapping(),
    ]
