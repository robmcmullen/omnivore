import os
import sys

# Major package imports.
import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Any, Bool, Int, Str, List, Dict, Event, Enum, DictStrStr

# Local imports.
import fonts
import colors
import disasm
import memory_map
import antic_renderers

class Machine(HasTraits):
    """ Collection of classes that identify a machine: processor, display, etc.
    
    """
    
    # Traits
    
    name = Str

    mime_prefix = Str("application/octet-stream")
    
    disassembler = Any(transient=True)
    
    memory_map = Any(transient=True)
    
    antic_font_data = Any
    
    antic_font = Any(transient=True)

    blinking_antic_font = Any(transient=True)
    
    antic_color_registers = Any
    
    color_standard = Enum(0, 1)
    
    color_registers = Any
    
    color_registers_highlight = Any
    
    color_registers_data = Any
    
    color_registers_match = Any
    
    color_registers_comment = Any
    
    bitmap_renderer = Any(transient=True)
    
    font_renderer = Any(transient=True)
    
    font_mapping = Any(transient=True)
    
    page_renderer = Any(transient=True)
    
    assembler = Any(transient=True)
    
    # Trait events
    
    font_change_event = Event
    
    bitmap_shape_change_event = Event
    
    bitmap_color_change_event = Event
    
    disassembler_change_event = Event
    
    # Class attributes (not traits)
    
    font_list = None
    
    emulator_list = None
    
    assembler_list = None
    
    highlight_color = (100, 200, 230)
    
    unfocused_cursor_color = (128, 128, 128)
    
    background_color = (255, 255, 255)
    
    data_color = (224, 224, 224)
    
    match_background_color = (255, 255, 180)
    
    comment_background_color = (255, 180, 200)
    
    empty_color = None
    
    text_color = (0, 0, 0)
    
    diff_text_color = (255, 0, 0)
    
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
    def init_emulators(cls, editor):
        if cls.emulator_list is None:
            cls.emulator_list = editor.window.application.get_json_data("emulator_list", [])
        default = editor.window.application.get_json_data("system_default_emulator", None)
        
        if default is None:
            default = cls.guess_system_default_emulator()
        if not cls.is_known_emulator(default):
            cls.emulator_list[0:0] = [default]
    
    @classmethod
    def remember_emulators(cls, application):
        e_list = []
        default = None
        for emu in cls.emulator_list:
            if 'system default' in emu:
                default = emu
            else:
                if 'system default' in emu:
                    # remove system default tags on any other emulator
                    del emu['system default']
                e_list.append(emu)
        if e_list:
            application.save_json_data("emulator_list", e_list)
        if default:
            application.save_json_data("system_default_emulator", default)
        
    @classmethod
    def init_assemblers(cls, editor):
        if cls.assembler_list is None:
            cls.assembler_list = editor.window.application.get_json_data("assembler_list", [])
        
        if not cls.assembler_list:
            cls.assembler_list = cls.guess_default_assemblers()
    
    @classmethod
    def remember_assemblers(cls, application):
        if cls.assembler_list:
            application.save_json_data("assembler_list", cls.assembler_list)
    
    @classmethod
    def init_colors(cls, editor):
        if cls.empty_color is None:
            attr = editor.control.GetDefaultAttributes()
            cls.empty_color = attr.colBg.Get(False)
    
    @classmethod
    def one_time_init(cls, editor):
        cls.init_fonts(editor)
        cls.init_colors(editor)
        cls.init_emulators(editor)
        cls.init_assemblers(editor)
    
    @classmethod
    def set_text_font(cls, editor, font, color):
        cls.text_color = color
        cls.text_font = font
        prefs = editor.task.get_preferences()
        prefs.text_font = font

    @classmethod
    def find_machine_by_mime(cls, mime):
        for m in predefined['machine']:
            if mime.startswith(m.mime_prefix):
                return m
    
    # Trait initializers
    
    def _name_default(self):
        return "Generic 6502"
    
    def _assembler_default(self):
        for asm in self.assembler_list:
            if 'system default' in asm:
                return asm
        return self.assembler_list[0]
    
    def _disassembler_default(self):
        return predefined['disassembler'][0]

    def _memory_map_default(self):
        return predefined['memory_map'][0]
    
    def _antic_font_default(self):
        return self.get_antic_font()
    
    def _blinking_antic_font_default(self):
        return self.get_antic_font(True)
    
    def _antic_font_data_default(self):
        return fonts.A8DefaultFont
    
    def _antic_color_registers_default(self):
        return list(colors.powerup_colors())
    
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
    
    def _color_registers_data_default(self):
        return self.get_dimmed_color_registers(self.color_registers, self.background_color, self.data_color)

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
        m = self.clone_traits()
        m.update_colors(m.antic_color_registers)
        m.set_font()
        return m
    #
    
    def update_colors(self, c):
        baseline = list(colors.powerup_colors())
        # need to operate on a copy of the colors to make sure we're not
        # changing some global value
        if len(c) == 5:
            baseline[4:9] = c
        else:
            baseline[0:len(c)] = c
        self.antic_color_registers = baseline
        self.color_registers = self.get_color_registers()
        self.color_registers_highlight = self.get_blended_color_registers(self.color_registers, self.highlight_color)
        self.color_registers_match = self.get_blended_color_registers(self.color_registers, self.match_background_color)
        self.color_registers_comment = self.get_blended_color_registers(self.color_registers, self.comment_background_color)
        self.set_font()
        self.bitmap_color_change_event = True
    
    def get_color_registers(self, antic_color_registers=None):
        color_converter = self.get_color_converter()
        registers = []
        if antic_color_registers is None:
            antic_color_registers = self.antic_color_registers
        for c in antic_color_registers:
            registers.append(color_converter(c))
        
        # make sure there are 16 registers for 4bpp modes
        i = len(registers)
        for i in range(len(registers), 16):
            registers.append((i*16, i*16, i*16))

        # Extend to 32 for dimmed copies of the 16 colors
        dim = []
        for r in registers:
            dim.append((r[0]/4 + 64, r[1]/4 + 64, r[2]/4 + 64))
        registers.extend(dim)
        return registers
    
    def get_blended_color_registers(self, colors, blend_color):
        registers = []
        base_blend = [(r * 7)/8 for r in blend_color]
        for c in colors:
            r = [c[i]/8 + base_blend[i] for i in range(3)]
            registers.append(r)
        return registers
    
    def get_dimmed_color_registers(self, colors, background_color, dimmed_color):
        registers = []
        dimmed_difference = [b - d for b, d in zip(background_color, dimmed_color)]
        for c in colors:
            r = [max(0, c[i]- dimmed_difference[i]) for i in range(3)]
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
        self.bitmap_shape_change_event = True
    
    def set_disassembler(self, disassembler):
        self.disassembler = disassembler
        self.disassembler_change_event = True
    
    def set_memory_map(self, memory_map):
        self.memory_map = memory_map
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
        if self.antic_font.use_blinking:
            self.blinking_antic_font = self.get_antic_font(True)
        else:
            self.blinking_antic_font = None
        self.set_font_mapping()

    def get_blinking_font(self, index):
        if self.antic_font.use_blinking and index == 1 and self.blinking_antic_font is not None:
            return self.blinking_antic_font
        else:
            return self.antic_font
    
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
    
    def get_antic_font(self, reverse=False):
        return fonts.AnticFont(self, self.antic_font_data, self.font_renderer, self.antic_color_registers[4:9], reverse)
    
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
            self.remember_fonts(task.window.application)
            task.machine_menu_changed = self
        except:
            raise
    
    def add_emulator(self, task, emu):
        self.emulator_list.append(emu)
        self.remember_emulators(task.window.application)
        task.machine_menu_changed = self
    
    @classmethod
    def is_known_emulator(cls, emu):
        for e in cls.emulator_list:
            if e == emu:
                return True
        return False
    
    @classmethod
    def guess_system_default_emulator(cls):
        if sys.platform == "win32":
            exe = "Altirra.exe"
        elif sys.platform == "darwin":
            exe = "Atari800MacX"
        else:
            exe = "atari800"
        emu = {'exe': exe,
               'args': "",
               'name': "system default: %s" % exe,
               'system default': True,
               }
        return emu
    
    @classmethod
    def get_system_default_emulator(cls, task):
        try:
            default = cls.emulator_list[0]
        except IndexError:
            # somehow, all the elements have been removed!
            default = cls.guess_system_default_emulator()
            cls.remember_emulators(task.window.application)
            task.machine_menu_changed = cls
        return default
    
    @classmethod
    def set_system_default_emulator(cls, task, emu):
        emu = dict(emu)  # copy to make sure we're not referencing an item in the existing emulator_list
        emu['system default'] = True
        emu['name'] = "system default: %s" % emu['name']
        default = cls.emulator_list[0]
        if 'system default' not in default:
            cls.emulator_list[0:0] = [emu]
        else:
            cls.emulator_list[0] = emu
        cls.remember_emulators(task.window.application)
        task.machine_menu_changed = cls
    
    @classmethod
    def get_user_defined_emulator_list(cls):
        """Return list of user defined emulators (i.e. not including the system
        default emulator
        """
        emus = []
        for e in cls.emulator_list:
            if 'system default' not in e:
                emus.append(e)
        return emus
    
    @classmethod
    def set_user_defined_emulator_list(cls, task, emus):
        default = None
        for e in cls.emulator_list:
            if 'system default' in e:
                default = e
        emus[0:0] = [default]
        cls.emulator_list = emus
        cls.remember_emulators(task.window.application)
        task.machine_menu_changed = cls
    
    def set_assembler(self, assembler):
        self.assembler = assembler
        self.disassembler_change_event = True
    
    def add_assembler(self, task, d):
        self.assembler_list.append(d)
        self.remember_assemblers(task.window.application)
        task.machine_menu_changed = self
    
    @classmethod
    def guess_default_assemblers(cls):
        asm_list = [
            {'comment char': ';',
             'origin': '.org',
             'data byte': '.byte',
             'name': "cc65",
             },
            {'comment char': ';',
             'origin': '*=',
             'data byte': '.byte',
             'name': "MAC/65",
             },
            ]
        return [dict(asm) for asm in asm_list]  # force a copy
    
    @classmethod
    def set_system_default_assembler(cls, task, asm):
        if 'system default' in asm:
            del asm['system default']
        for e in cls.assembler_list:
            if 'system default' in e:
                del e['system default']
        found = False
        for e in cls.assembler_list:
            if e == asm:
                asm['system default'] = True
                found = True
                break
        if not found:
            cls.assembler_list[0:0] = [asm]
        cls.remember_assemblers(task.window.application)
        task.machine_menu_changed = cls
    
    @classmethod
    def get_default_assembler(cls):
        found = None
        for e in cls.assembler_list:
            if 'system default' in e:
                found = e
        if not found:
            if cls.assembler_list:
                found = cls.assembler_list[0]
        return found

    @classmethod
    def set_assembler_list(cls, task, asms):
        default = None
        for e in asms:
            if 'system default' in e:
                if default:
                    del e['system default']
                else:
                    default = e
        cls.assembler_list = asms
        cls.remember_assemblers(task.window.application)
        task.machine_menu_changed = cls
    
    def verify_current_assembler(self):
        found = None
        for asm in self.assembler_list:
            if self.assembler == asm:
                found = asm
                break
        if not found:
            asm = self.get_default_assembler()
        self.set_assembler(asm)
    
    # Utility methods
    
    def get_disassembler(self, hex_lower, mnemonic_lower):
        return self.disassembler(self.assembler, self.memory_map, hex_lower, mnemonic_lower)


Generic6502 = Machine(name="Generic 6502", disassembler=disasm.Basic6502Disassembler)

Atari800 = Machine(name="Atari 800", mime_prefix="application/vnd.atari8bit", disassembler=disasm.Basic6502Disassembler, memory_map=memory_map.Atari800MemoryMap)

Atari800Undoc = Machine(name="Atari 800 (show undocumented opcodes)", mime_prefix="application/vnd.atari8bit", disassembler=disasm.Undocumented6502Disassembler, memory_map=memory_map.Atari800MemoryMap)

Atari800Flagged = Machine(name="Atari 800 (highlight undocumented opcodes)", mime_prefix="application/vnd.atari8bit", disassembler=disasm.Flagged6502Disassembler, memory_map=memory_map.Atari800MemoryMap)

Atari5200 = Machine(name="Atari 5200", mime_prefix="application/vnd.atari8bit", disassembler=disasm.Basic6502Disassembler, memory_map=memory_map.Atari5200MemoryMap)



predefined = {
    "machine": [
        Generic6502,
        Atari800,
        Atari800Undoc,
        Atari800Flagged,
        Atari5200,
        ],
    "memory_map": [
        memory_map.EmptyMemoryMap,
        memory_map.Atari800MemoryMap,
        memory_map.Atari5200MemoryMap,
        memory_map.Apple2MemoryMap,
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
        antic_renderers.OneBitPerPixelApple2(),
        antic_renderers.ModeD(),
        antic_renderers.ModeE(),
        antic_renderers.GTIA9(),
        antic_renderers.GTIA10(),
        antic_renderers.GTIA11(),
        antic_renderers.TwoBitsPerPixel(),
        antic_renderers.FourBitsPerPixel(),
        antic_renderers.TwoBitPlanesLE(),
        antic_renderers.TwoBitPlanesLineLE(),
        antic_renderers.TwoBitPlanesBE(),
        antic_renderers.TwoBitPlanesLineBE(),
        antic_renderers.ThreeBitPlanesLE(),
        antic_renderers.ThreeBitPlanesLineLE(),
        antic_renderers.ThreeBitPlanesBE(),
        antic_renderers.ThreeBitPlanesLineBE(),
        antic_renderers.FourBitPlanesLE(),
        antic_renderers.FourBitPlanesLineLE(),
        antic_renderers.FourBitPlanesBE(),
        antic_renderers.FourBitPlanesLineBE(),
        ],
    "font_renderer": [
        antic_renderers.Mode2(),
        antic_renderers.Mode4(),
        antic_renderers.Mode5(),
        antic_renderers.Mode6Upper(),
        antic_renderers.Mode6Lower(),
        antic_renderers.Mode7Upper(),
        antic_renderers.Mode7Lower(),
        antic_renderers.Apple2TextMode(),
        ],
    "font_mapping": [
        antic_renderers.ATASCIIFontMapping(),
        antic_renderers.AnticFontMapping(),
        ],
    "page_renderer": [
        antic_renderers.BytePerPixelMemoryMap(),
        ],
    }


Apple2 = Machine(name="Apple ][", mime_prefix="application/vnd.apple2", disassembler=disasm.Basic65C02Disassembler, antic_font_data=fonts.A2DefaultFont, font_renderer=predefined['font_renderer'][7], font_mapping=predefined['font_mapping'][1], antic_color_registers=[4, 30, 68, 213, 15, 202, 148, 70, 0], memory_map=memory_map.Apple2MemoryMap)
predefined['machine'].append(Apple2)
