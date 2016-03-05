import os

# Major package imports.
import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Any, Bool, Int, Str, List, Dict, Event, Enum, DictStrStr

# Local imports.
import fonts
import colors
import disasm
import machine_atari800
import machine_atari5200
import antic_renderers

class Machine(HasTraits):
    """ Collection of classes that identify a machine: processor, display, etc.
    
    """
    
    # Traits
    
    name = Str
    
    disassembler = Any(transient=True)
    
    memory_map = Dict(key_trait=Int, value_trait=Str)
    
    antic_font_data = Any
    
    antic_font = Any(transient=True)
    
    antic_color_registers = Any
    
    color_standard = Enum(0, 1)
    
    color_registers = Any
    
    color_registers_highlight = Any
    
    color_registers_match = Any
    
    color_registers_comment = Any
    
    bitmap_renderer = Any(transient=True)
    
    font_renderer = Any(transient=True)
    
    font_mapping = Any(transient=True)
    
    page_renderer = Any(transient=True)
    
    # Trait events
    
    font_change_event = Event
    
    bitmap_change_event = Event
    
    disassembler_change_event = Event
    
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
        try:
            cls.text_font = prefs.text_font
        except AttributeError:
            pass
    
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
        return predefined['disassembler'][0]

    def _memory_map_default(self):
        return {}
    
    def _antic_font_default(self):
        return self.get_antic_font()
    
    def _antic_font_data_default(self):
        return fonts.A8DefaultFont
    
    def _antic_color_registers_default(self):
        return colors.powerup_colors()
    
    def _color_standard_default(self):
        return 0  # NTSC
    
    def _color_registers_default(self):
        return self.get_color_registers()
    
    def _color_registers_highlight_default(self):
        return self.get_blended_color_registers(self.color_registers, self.highlight_color)
    
    def _color_registers_match_default(self):
        return self.get_blended_color_registers(self.color_registers, self.match_background_color)
    
    def _color_registers_comment_default(self):
        return self.get_blended_color_registers(self.color_registers, self.comment_background_color)

    def _bitmap_renderer_default(self):
        return predefined['bitmap_renderer'][0]
    
    def _font_renderer_default(self):
        return predefined['font_renderer'][0]
    
    def _font_mapping_default(self):
        return predefined['font_mapping'][0]
    
    def _page_renderer_default(self):
        return predefined['page_renderer'][0]
    
    def __getstate__(self):
        state = super(Machine, self).__getstate__()
        
        for name in self.all_trait_names():
            t = self.trait(name)
            if t.transient:
                if name in predefined:
                    value = getattr(self, name)
                    state[name] = predefined[name].index(value)
            elif name == "memory_map":
                # convert into list of tuples so json won't mangle the integer
                # keys into strings
                value = getattr(self, name)
                state[name] = value.items()
        
        print state.keys()
        return state
    
    def __setstate__(self, state):
        for name in self.all_trait_names():
            t = self.trait(name)
            if t.transient:
                if name in predefined:
                    index = state[name]
                    setattr(self, name, predefined[name][index])
            elif name == "memory_map":
                # convert into list of tuples so json won't mangle the integer
                # keys into strings
                value = state[name]
                setattr(self, name, {k:v for k,v in value})
            else:
                try:
                    setattr(self, name, state[name])
                except KeyError:
                    pass
    
        # set up trait notifications
        self._init_trait_listeners()
    # 
    
    def __eq__(self, other):
        return self.disassembler == other.disassembler and self.memory_map == other.memory_map

    def clone_machine(self):
        return self.clone_traits()
    
    #
    
    def update_colors(self, colors):
        if len(colors) == 5:
            self.antic_color_registers[4:9] = colors
        else:
            self.antic_color_registers = colors
        self.color_registers = self.get_color_registers()
        self.color_registers_highlight = self.get_blended_color_registers(self.color_registers, self.highlight_color)
        self.color_registers_match = self.get_blended_color_registers(self.color_registers, self.match_background_color)
        self.color_registers_comment = self.get_blended_color_registers(self.color_registers, self.comment_background_color)
        self.set_font()
        self.bitmap_change_event = True
    
    def get_color_registers(self, antic_color_registers=None):
        color_converter = self.get_color_converter()
        registers = []
        if antic_color_registers is None:
            antic_color_registers = self.antic_color_registers
        for c in antic_color_registers:
            registers.append(color_converter(c))
        return registers
    
    def get_blended_color_registers(self, colors, blend_color):
        registers = []
        base_blend = [(r * 7)/8 for r in blend_color]
        for c in colors:
            r = [c[i]/8 + base_blend[i] for i in range(3)]
            registers.append(r)
        return registers
    
    def get_color_converter(self):
        if self.color_standard == 0:
            return colors.gtia_ntsc_to_rgb
        return colors.gtia_pal_to_rgb
    
    def set_color_standard(self, std):
        self.color_standard = std
        self.update_colors(self.antic_color_registers)
    
    def set_bitmap_renderer(self, renderer):
        self.bitmap_renderer = renderer
        self.bitmap_change_event = True
    
    def set_disassembler(self, disassembler):
        self.disassembler = disassembler
        self.disassembler_change_event = True
    
    def set_font(self, font=None, font_renderer=None):
        if font is None:
            font = self.antic_font_data
        if font_renderer is not None:
            try:
                font_mode = int(font_renderer)
                font_renderer = self.get_font_renderer_from_font_mode(font_mode)
            except TypeError:
                pass
            self.font_renderer = font_renderer
        self.antic_font_data = font
        self.antic_font = self.get_antic_font()
        self.set_font_mapping()
    
    def get_font_renderer_from_font_mode(self, font_mode):
        for r in predefined['font_renderer']:
            if r.font_mode == font_mode:
                return r
        return predefined['font_renderer'][0]
    
    def set_font_mapping(self, font_mapping=None):
        if font_mapping is None:
            font_mapping = self.font_mapping
        self.font_mapping = font_mapping
        self.font_change_event = True
    
    def get_antic_font(self):
        color_converter = self.get_color_converter()
        return fonts.AnticFont(self, self.antic_font_data, self.font_renderer.font_mode, self.antic_color_registers[4:9])
    
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


Generic6502 = Machine(name="Generic 6502", disassembler=disasm.Basic6502Disassembler)

Atari800 = Machine(name="Atari 800", disassembler=disasm.Basic6502Disassembler, memory_map=dict(machine_atari800.memmap))

Atari800Undoc = Machine(name="Atari 800 (show undocumented opcodes)", disassembler=disasm.Undocumented6502Disassembler, memory_map=dict(machine_atari800.memmap))

Atari800Flagged = Machine(name="Atari 800 (highlight undocumented opcodes)", disassembler=disasm.Flagged6502Disassembler, memory_map=dict(machine_atari800.memmap))

Atari5200 = Machine(name="Atari 5200", disassembler=disasm.Basic6502Disassembler, memory_map=dict(machine_atari5200.memmap))



predefined = {
    "machine": [
        Generic6502,
        Atari800,
        Atari800Undoc,
        Atari800Flagged,
        Atari5200,
        ],
    "disassembler": [
        disasm.Basic6502Disassembler,
        disasm.Undocumented6502Disassembler,
        disasm.Flagged6502Disassembler,
        disasm.Basic65C02Disassembler,
        disasm.Basic65816Disassembler,
        disasm.Basic6800Disassembler,
        disasm.Basic6809Disassembler,
        disasm.Basic6811Disassembler,
        disasm.Basic8051Disassembler,
        disasm.Basic8080Disassembler,
        disasm.BasicZ80Disassembler,
        ],
    "bitmap_renderer": [
        antic_renderers.OneBitPerPixelB(),
        antic_renderers.OneBitPerPixelW(),
        antic_renderers.ModeE(),
        antic_renderers.GTIA9(),
        antic_renderers.GTIA10(),
        antic_renderers.GTIA11(),
        ],
    "font_renderer": [
        antic_renderers.Mode2(),
        antic_renderers.Mode4(),
        antic_renderers.Mode5(),
        antic_renderers.Mode6Upper(),
        antic_renderers.Mode6Lower(),
        antic_renderers.Mode7Upper(),
        antic_renderers.Mode7Lower(),
        ],
    "font_mapping": [
        antic_renderers.ATASCIIFontMapping(),
        antic_renderers.AnticFontMapping(),
        ],
    "page_renderer": [
        antic_renderers.BytePerPixelMemoryMap(),
        ],
    }

