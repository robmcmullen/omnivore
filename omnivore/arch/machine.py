import os
import sys

# Major package imports.
import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Any, Bool, Int, Str, List, Dict, Enum, DictStrStr

from sawx import persistence
from sawx.events import EventHandler

# Local imports.
from . import fonts
from atrip.machines import atari8bit
from . import disasm
from . import memory_map
# from . import antic_renderers

import logging
log = logging.getLogger(__name__)


def restore_from_last_time():
    log.debug("Restoring Machine config")
    init_font_list()
    init_assemblers()

def init_font_list():
    try:
        Machine.font_list = persistence.get_bson_data("font_list")
    except IOError:
        # file not found
        Machine.font_list = []
    except ValueError:
        # bad JSON format
        Machine.font_list = []

def init_assemblers():
    if Machine.assembler_list is None:
        Machine.assembler_list = persistence.get_json_data("assembler_list", [])

        # With built-in MAC/65 compilation support, fix the list of default
        # assemblers to change the default assembler to MAC/65 if the user
        # hasn't made an alteration to the list.
        a = Machine.assembler_list
        if len(a) == 2 and a[0]['name'] == "cc65" and a[1]['name'] == "MAC/65":
            Machine.assembler_list = None

    if not Machine.assembler_list:
        Machine.assembler_list = Machine.guess_default_assemblers()

def remember_for_next_time():
    log.debug("Remembering Machine config")
    if Machine.font_list:
        persistence.save_bson_data("font_list", Machine.font_list)
    if Machine.assembler_list:
        persistence.save_json_data("assembler_list", Machine.assembler_list)


class Machine(HasTraits):
    """ Collection of classes that identify a machine: processor, display, etc.

    """

    # Traits

    name = Str

    mime_prefix = Str("application/octet-stream")

    disassembler = Any(transient=True)

    memory_map = Any(transient=True)

    antic_font_data = Any

    antic_color_registers = Any

    color_standard = Enum(0, 1)

    color_registers = Any(transient=True)

    bitmap_renderer = Any(transient=True)

    font_renderer = Any(transient=True)

    font_mapping = Any(transient=True)

    page_renderer = Any(transient=True)

    assembler = Any(transient=True)

    machine_metadata_changed_event = Any

    # Class attributes (not traits)

    font_list = None

    assembler_list = None

    text_font = None

    @classmethod
    def find_machine_by_mime(cls, mime, default_if_not_matched=False):
        for m in predefined['machine']:
            if mime.startswith(m.mime_prefix):
                return m
        if default_if_not_matched:
            return predefined['machine'][0]

    # Trait initializers

    def _machine_metadata_changed_event_default(self):
        return EventHandler(self, debug=True)

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

    def _antic_font_data_default(self):
        return fonts.A8DefaultFont

    def _antic_color_registers_default(self):
        return list(colors.powerup_colors())

    def _color_standard_default(self):
        return 0  # NTSC

    def _color_registers_default(self):
        return self.get_color_registers()

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
        try:
            del state["__traits_version__"]
        except KeyError:
            pass

        for name in self.all_trait_names():
            t = self.trait(name)
            if t.transient:
                if name in predefined:
                    value = getattr(self, name)
                    try:
                        state[name] = predefined[name].index(value)
                    except ValueError:
                        log.warning("No matching index for predefined[%s]; will use default upon load instead of %s" % (name, value))
            elif name == "memory_map":
                # convert into list of tuples so json won't mangle the integer
                # keys into strings
                value = getattr(self, name)
                state[name] = list(value.items())
            elif name == "antic_font_data":
                value = getattr(self, name)
                state[name] = value['uuid']
        return state

    def state_to_traits(self, state):
        for name in self.all_trait_names():
            if name not in state:
                # skip missing trait definitions
                continue
            log.debug("state_to_traits: %s, restoring from %s" % (name, state.get(name, None)))
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
            elif name == "antic_font_data":
                uuid = state[name]
                try:
                    font_data = fonts.builtin_font_data[uuid]
                except KeyError:
                    font_data = fonts.A8DefaultFont
                except TypeError:
                    # loading omnivore 1.0 format
                    log.error("found Omnivore 1.0 font segment")
                    font_data = fonts.A8DefaultFont
                setattr(self, name, font_data)
            else:
                try:
                    setattr(self, name, state[name])
                except KeyError:
                    pass

    def __setstate__(self, state):
        self.state_to_traits(state)
        # set up trait notifications
        self._init_trait_listeners()
    #

    def __eq__(self, other):
        return self.disassembler == other.disassembler and self.memory_map == other.memory_map

    # to be usable in dicts, py3 needs __hash__ defined if __eq__ is defined
    def __hash__(self):
        return id(self)

    def clone_machine(self):
        m = self.clone_traits()
        m.update_colors(m.antic_color_registers)
        return m

    def serialize_extra_to_dict(self, mdict):
        """Save extra metadata to a dict so that it can be serialized
        """
        s = self.__getstate__()
        mdict.update(s)

    def restore_extra_from_dict(self, e):
        self.state_to_traits(e)
        self.update_colors(self.antic_color_registers)
    #

    def update_colors(self, c):
        baseline = list(colors.powerup_colors())
        # need to operate on a copy of the colors to make sure we're not
        # changing some global value. Also force as python int so we're not
        # mixing numpy and python values.
        if len(c) == 5:
            baseline[4:9] = [int(i) for i in c]
        else:
            baseline[0:len(c)] = [int(i) for i in c]
        self.antic_color_registers = baseline
        self.color_registers = self.get_color_registers()
        print("COLOR REGISTERS", self.color_registers)
        self.machine_metadata_changed_event(True)

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

    def get_color_converter(self):
        if self.color_standard == 0:
            return colors.gtia_ntsc_to_rgb
        return colors.gtia_pal_to_rgb

    def set_color_standard(self, std):
        self.color_standard = std
        self.update_colors(self.antic_color_registers)

    @property
    def color_standard_name(self):
        return "NTSC" if self.color_standard == 0 else "PAL"

    def set_bitmap_renderer(self, renderer):
        self.bitmap_renderer = renderer
        self.bitmap_shape_change_event = True

    def set_disassembler(self, disassembler):
        self.disassembler = disassembler
        self.disassembler_change_event = True

    def set_memory_map(self, memory_map):
        self.memory_map = memory_map
        self.disassembler_change_event = True

    def get_font_renderer_from_font_name(self, font_name):
        for r in predefined['font_renderer']:
            if r.name.startswith(font_name):
                return r
        return predefined['font_renderer'][0]

    def get_font_mapping_from_name(self, name):
        for r in predefined['font_mapping']:
            if r.name.startswith(name):
                return r
        return predefined['font_mapping'][0]

    def set_font_mapping(self, font_mapping=None):
        if font_mapping is None:
            font_mapping = self.font_mapping
        elif isinstance(font_mapping, str):
            font_mapping = self.get_font_mapping_from_name(font_mapping)
        self.font_mapping = font_mapping
        self.font_change_event = True

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
             'origin': '*=',
             'data byte': '.byte',
             'data byte prefix': '$',
             'data byte separator': ', ',
             'name': "MAC/65",
             },
            {'comment char': ';',
             'origin': '.org',
             'data byte': '.byte',
             'data byte prefix': '$',
             'data byte separator': ', ',
             'name': "cc65",
             },
            {'comment char': ';',
             'origin': '.org',
             'data byte': '.byte',
             'data byte prefix': '$',
             'data byte separator': ', ',
             'name': "MADS",
             },
            {'comment char': ';',
             'origin': 'org',
             'data byte': 'hex',
             'data byte prefix': '',
             'data byte separator': '',
             'name': "Merlin",
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

    def get_disassembler(self, hex_lower, mnemonic_lower, document_memory_map=None, segment_memory_map=None):
        if not document_memory_map and not segment_memory_map:  # either None or empty dict
            mmap = self.memory_map()
        else:
            # Create a merged memory map with first the segment map then the
            # document map taking precedence over the machine memory map when
            # there are duplicates
            parent = memory_map.EmptyMemoryMap
            mmap = parent.__class__("CustomMemoryMap", (parent,), {"rmemmap": dict(self.memory_map.rmemmap), "wmemmap": dict(self.memory_map.wmemmap)})
            if document_memory_map:
                mmap.rmemmap.update(document_memory_map)
            if segment_memory_map:
                mmap.rmemmap.update(segment_memory_map)
        return self.disassembler(self.assembler, mmap, hex_lower, mnemonic_lower)

    def get_nop(self):
        return self.disassembler.get_nop()


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
        memory_map.KIM1MemoryMap,
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
    # "bitmap_renderer": [
    #     antic_renderers.OneBitPerPixelB(),
    #     antic_renderers.OneBitPerPixelW(),
    #     antic_renderers.OneBitPerPixelPM1(),
    #     antic_renderers.OneBitPerPixelPM2(),
    #     antic_renderers.OneBitPerPixelPM4(),
    #     antic_renderers.OneBitPerPixelApple2Linear(),
    #     antic_renderers.ModeB(),
    #     antic_renderers.ModeC(),
    #     antic_renderers.ModeD(),
    #     antic_renderers.ModeE(),
    #     antic_renderers.GTIA9(),
    #     antic_renderers.GTIA10(),
    #     antic_renderers.GTIA11(),
    #     antic_renderers.TwoBitsPerPixel(),
    #     antic_renderers.FourBitsPerPixel(),
    #     antic_renderers.TwoBitPlanesLE(),
    #     antic_renderers.TwoBitPlanesLineLE(),
    #     antic_renderers.TwoBitPlanesBE(),
    #     antic_renderers.TwoBitPlanesLineBE(),
    #     antic_renderers.ThreeBitPlanesLE(),
    #     antic_renderers.ThreeBitPlanesLineLE(),
    #     antic_renderers.ThreeBitPlanesBE(),
    #     antic_renderers.ThreeBitPlanesLineBE(),
    #     antic_renderers.FourBitPlanesLE(),
    #     antic_renderers.FourBitPlanesLineLE(),
    #     antic_renderers.FourBitPlanesBE(),
    #     antic_renderers.FourBitPlanesLineBE(),
    #     ],
    # "font_renderer": [
    #     antic_renderers.Mode2(),
    #     antic_renderers.Mode4(),
    #     antic_renderers.Mode5(),
    #     antic_renderers.Mode6Upper(),
    #     antic_renderers.Mode6Lower(),
    #     antic_renderers.Mode7Upper(),
    #     antic_renderers.Mode7Lower(),
    #     antic_renderers.Apple2TextMode(),
    #     ],
    # "font_mapping": [
    #     antic_renderers.ATASCIIFontMapping(),
    #     antic_renderers.AnticFontMapping(),
    #     ],
    # "page_renderer": [
    #     antic_renderers.BytePerPixelMemoryMap(),
    #     ],
    }


# Apple2 = Machine(name="Apple ][", mime_prefix="application/vnd.apple2", disassembler=disasm.Basic65C02Disassembler, antic_font_data=fonts.A2DefaultFont, font_renderer=predefined['font_renderer'][7], font_mapping=predefined['font_mapping'][1], antic_color_registers=[4, 30, 68, 213, 15, 202, 148, 70, 0], memory_map=memory_map.Apple2MemoryMap)
# predefined['machine'].append(Apple2)
