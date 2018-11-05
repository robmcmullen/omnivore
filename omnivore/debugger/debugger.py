"""Debugger interface mimicking GDB

info|i
  breakpoints (bp)   List breakpoints
  cpu  show CPU registers
  antic
  pokey
  gtia


break|b ADDRESS|LABEL|+OFFSET|-OFFSET [if CONDITION]
  ADDRESS:
    literal hex address at which to break
  LABEL:
    break at address stored in LABEL
  +OFFSET
    break at current address + offset
  -OFFSET
    break at current address - offset
  CONDITION:
    an expression that evaluates to a boolean, triggering the breakpoint when
    true.  E.g. (A > 10 and (X < 0x80 and not C))


watch|w CONDITION
  CONDITION:
    same as above (watchpoints are the same as breakpoints without an address)


tbreak|t COMMAND [if CONDITION]
  Temporary break: break once only and then it is removed. See "break" above.


delete|d [BREAKPOINT[-RANGE]]
  Delete breakpoints

  BREAKPOINT:
    delete specified breakpoint
  RANGE:
    delete range from BREAKPOINT to RANGE

  No argument: delete all breakpoints


disable|di [BREAKPOINT[-RANGE]]
  Disable breakpoints, specifiers as above


enable|en [BREAKPOINT[-RANGE]]
  Enable breakpoints, specifiers as above


continue|c [COUNT]
  Continue executing until next breakpoint

  COUNT:
    Continue, but ignore current breakpoint NUMBER times


finish|f
  Continue to end of function


step|s [NUMBER]
  Step to next line, will step into functions

  NUMBER:
    number of steps to perform


next|n [NUMBER]
  Next line, stepping over function calls


until|u [ADDRESS|LABEL]
  Continue until reaching address


NON-GDB commands:

ccontinue|cc NUMBER
  Continue executing under NUMBER cycles has been reached.


"""

import numpy as np

from . import dtypes as dd
from ..utils.persistence import Serializable

import logging
log = logging.getLogger(__name__)


class Breakpoint:
    def __init__(self, debugger, id, addr=None):
        self.debugger = debugger
        self.id = id
        self.index = id * dd.TOKENS_PER_BREAKPOINT
        if addr is not None:
            self.simple_address(addr)

    def __str__(self):
        if self.id == 0:
            ref = self.reference_value
        else:
            ref = "n/a"
        return f"<breakpoint {self.id}, status={self.status}, type={self.type}, ref_val={ref} terms={self.terms}>"

    @property
    def status(self):
        c = self.debugger.debug_cmd[0]
        return c['breakpoint_status'][self.id]

    @status.setter
    def status(self, status):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = status

    @property
    def type(self):
        c = self.debugger.debug_cmd[0]
        return c['breakpoint_type'][self.id]

    @type.setter
    def type(self, type):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = type

    @property
    def reference_value(self):
        c = self.debugger.debug_cmd[0]
        return c['reference_value'][self.id]

    @reference_value.setter
    def reference_value(self, type):
        c = self.debugger.debug_cmd[0]
        c['reference_value'][self.id] = reference_value

    @property
    def terms(self):
        c = self.debugger.debug_cmd[0]
        i = self.index
        tokens = c['tokens'][i:i+dd.TOKENS_PER_BREAKPOINT]
        end_tokens = np.where(tokens == dd.END_OF_LIST)[0]
        return tokens[:end_tokens[0]]

    @terms.setter
    def terms(self, term_list):
        c = self.debugger.debug_cmd[0]
        i = self.index
        count = len(term_list)
        c['tokens'][i:i+count] = term_list

    @property
    def enabled(self):
        c = self.debugger.debug_cmd[0]
        return bool(c['breakpoint_status'][self.id] == dd.BREAKPOINT_ENABLED)

    @property
    def had_error(self):
        c = self.debugger.debug_cmd[0]
        return bool(c['breakpoint_status'][self.id] & dd.BREAKPOINT_ERROR)

    def simple_address(self, addr):
        # shortcut to create a PC=addr breakpoint
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_CONDITIONAL
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        self.terms = (dd.REG_PC, dd.NUMBER, addr, dd.OP_EQ, dd.END_OF_LIST)

    def step_into(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_COUNT_INSTRUCTIONS
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        c['reference_value'][self.id] = self.debugger.instructions_since_power_on
        c['tokens'][self.index] = count
        self.enable()

    def break_vbi_start(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_CONDITIONAL
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        c['tokens'][self.index] = count
        self.terms = (dd.EMU_VBI_START, dd.END_OF_LIST)
        self.enable()

    def count_cycles(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_COUNT_CYCLES
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        c['reference_value'][self.id] = self.debugger.cycles_since_power_on
        c['tokens'][self.index] = count
        self.enable()

    def count_frames(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_COUNT_FRAMES
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        c['reference_value'][self.id] = self.debugger.current_frame_number
        c['tokens'][self.index] = count
        self.enable()

    def break_at_return(self):
        # shortcut to create a PC=addr breakpoint
        c = self.debugger.debug_cmd[0]
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_CONDITIONAL
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        sp = self.debugger.stack_pointer
        self.terms = (dd.OPCODE_TYPE, dd.OPCODE_RETURN, dd.REG_SP, dd.NUMBER, sp, dd.OP_EQ, dd.OP_LOGICAL_AND, dd.END_OF_LIST)
        self.enable()

    def clear(self):
        c = self.debugger.debug_cmd[0]
        status = dd.BREAKPOINT_DISABLED if self.id == 0 else dd.BREAKPOINT_EMPTY
        c['breakpoint_type'][self.id] = dd.BREAKPOINT_CONDITIONAL
        c['breakpoint_status'][self.id] = status
        c['tokens'][self.index] = dd.END_OF_LIST

    def enable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        if self.id >= c['num_breakpoints']:
            c['num_breakpoints'] = self.id + 1

    def disable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_DISABLED


class Debugger(Serializable):
    name = "<name>"

    serializable_attributes = ['debug_cmd_raw']
    serializable_computed = {'debug_cmd_raw'}

    def __init__(self):
        self.debug_cmd_raw = np.zeros([dd.DEBUGGER_COMMANDS_DTYPE.itemsize], dtype=np.uint8)
        self.debug_cmd = self.debug_cmd_raw.view(dtype=dd.DEBUGGER_COMMANDS_DTYPE)
        self.clear_all_breakpoints()

    ##### Serialization

    def restore_computed_attributes(self, state):
        self.debug_cmd_raw[:] = state['debug_cmd_raw']

    def clear_all_breakpoints(self):
        c = self.debug_cmd[0]
        c['breakpoint_type'][:] = dd.BREAKPOINT_CONDITIONAL
        c['breakpoint_status'][:] = 0
        c['breakpoint_status'][0] = dd.BREAKPOINT_DISABLED
        c['num_breakpoints'] = 0
        c['last_pc'] = -1

    def create_breakpoint(self, addr=None):
        c = self.debug_cmd[0]
        empty = np.where(c['breakpoint_status'] == dd.BREAKPOINT_EMPTY)[0]
        bpid = empty[0]
        c['num_breakpoints'] = max(c['num_breakpoints'], bpid + 1)
        return Breakpoint(self, bpid, addr)

    def get_breakpoint(self, bpid):
        if bpid < 0:
            return None
        return Breakpoint(self, bpid)

    def step_into(self, number=1):
        b = Breakpoint(self, 0)
        b.step_into(number)

    def break_vbi_start(self, number=1):
        b = Breakpoint(self, 0)
        b.break_vbi_start(number)

    def count_frames(self, number=1):
        b = Breakpoint(self, 0)
        b.count_frames(number)

    def count_cycles(self, cycles=1):
        b = Breakpoint(self, 0)
        b.count_cycles(number)

    def iter_breakpoints(self):
        for i in range(dd.NUM_BREAKPOINT_ENTRIES):
            b = Breakpoint(self, i)
            if b.enabled:
                yield b

    def print_breakpoints(self):
        for b in self.iter_breakpoints():
            print(b)
