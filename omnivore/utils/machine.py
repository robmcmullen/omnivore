import os

# Major package imports.
import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Any, Bool, Int, Str, List, Dict

# Local imports.
from dis6502 import Basic6502Disassembler, Undocumented6502Disassembler, Flagged6502Disassembler
import machine_atari800
import machine_atari5200

class Machine(HasTraits):
    """ Collection of classes that identify a machine: processor, display, etc.
    
    """
    name = Str
    
    disassembler = Any
    
    memory_map = Dict
    
    def _name_default(self):
        return "Generic 6502"
    
    def _disassembler_default(self):
        return Basic6502Disassembler

    def _memory_map_default(self):
        return {}
    
    def __eq__(self, other):
        return self.disassembler == other.disassembler and self.memory_map == other.memory_map

    def clone_machine(self):
        return self.clone_traits()
    
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
