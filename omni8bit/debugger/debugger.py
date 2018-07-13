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
        return f"<breakpoint {self.id}, condition index={self.index}, terms={self.terms}>"

    @property
    def status(self):
        c = self.debugger.debug_cmd[0]
        return c['breakpoint_status'][self.id]

    @status.setter
    def status(self, status):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = status

    @property
    def terms(self):
        c = self.debugger.debug_cmd[0]
        i = self.index
        tokens = c['tokens'][i:i+dd.TOKENS_PER_BREAKPOINT]
        end_tokens = np.where(tokens == dd.END_OF_LIST)[0]
        return tokens[:end_tokens[0]]

    def simple_address(self, addr):
        # shortcut to create a PC=addr breakpoint
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        i = self.index
        c['tokens'][i:i+5] = (dd.REG_PC, dd.NUMBER, addr, dd.OP_EQ, dd.END_OF_LIST)

    def step_into(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_COUNT_INSTRUCTIONS
        c['tokens'][self.index] = count

    def count_cycles(self, count):
        # shortcut to create a break after `count` instructions
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_COUNT_CYCLES
        c['tokens'][self.index] = count

    def clear(self):
        c = self.debugger.debug_cmd[0]
        status = dd.BREAKPOINT_DISABLED if self.id == 0 else dd.BREAKPOINT_EMPTY
        c['breakpoint_status'][self.id] = status
        c['tokens'][self.index] = dd.END_OF_LIST

    def enable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED

    def disable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_DISABLED


class Debugger:
    def __init__(self):
        self.debug_cmd_raw = np.zeros([dd.DEBUGGER_COMMANDS_DTYPE.itemsize], dtype=np.uint8)
        self.debug_cmd = self.debug_cmd_raw.view(dtype=dd.DEBUGGER_COMMANDS_DTYPE)
        self.clear_all_breakpoints()

    def clear_all_breakpoints(self):
        c = self.debug_cmd[0]
        c['breakpoint_status'][:] = 0
        c['breakpoint_status'][0] = dd.BREAKPOINT_DISABLED
        c['num_breakpoints'] = 0

    def create_breakpoint(self, addr=None):
        c = self.debug_cmd[0]
        empty = np.where(c['breakpoint_status'] == dd.BREAKPOINT_EMPTY)[0]
        bpid = empty[0]
        if bpid >= c['num_breakpoints']:
            c['num_breakpoints'] = bpid + 1
        c['breakpoint_status'][bpid] = dd.BREAKPOINT_ENABLED
        return Breakpoint(self, bpid, addr)

    def get_breakpoint(self, bpid):
        return Breakpoint(self, bpid)

    def get_watchpoint(self, bpid):
        return Watchpoint(self, bpid)

    def step_into(self, number=1):
        b = Breakpoint(self, 0)
        b.step_into(number)

    def count_cycles(self, cycles=1):
        b = Breakpoint(self, 0)
        b.count_cycles(number)
