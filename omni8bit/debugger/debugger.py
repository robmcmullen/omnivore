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

    def clear(self):
        c = self.debugger.debug_cmd[0]
        status = dd.BREAKPOINT_RESERVED if self.id == 0 else dd.BREAKPOINT_EMPTY
        c['breakpoint_status'][self.id] = status
        c['tokens'][self.index] = dd.END_OF_LIST

    def enable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED

    def disable(self):
        c = self.debugger.debug_cmd[0]
        status = dd.BREAKPOINT_RESERVED if self.id == 0 else dd.BREAKPOINT_DISABLED
        c['breakpoint_status'][self.id] = status


class Debugger:
    def __init__(self):
        self.debug_cmd_raw = np.zeros([dd.DEBUGGER_COMMANDS_DTYPE.itemsize], dtype=np.uint8)
        self.debug_cmd = self.debug_cmd_raw.view(dtype=dd.DEBUGGER_COMMANDS_DTYPE)
        self.clear_all_breakpoints()

    def clear_all_breakpoints(self):
        c = self.debug_cmd[0]
        c['breakpoint_status'][:] = 0
        c['breakpoint_status'][0] = dd.BREAKPOINT_RESERVED
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
