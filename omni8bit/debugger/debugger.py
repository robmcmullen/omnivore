import numpy as np

from . import dtypes as dd

import logging
log = logging.getLogger(__name__)


class Breakpoint:
    def __init__(self, debugger, id, addr=None):
        self.debugger = debugger
        self.id = id
        if addr is not None:
            self.address = addr

    def __str__(self):
        return f"<breakpoint {self.id} at {hex(self.address)}>"

    @property
    def address(self):
        c = self.debugger.debug_cmd[0]
        return c['breakpoint_address'][self.id]

    @address.setter
    def address(self, addr):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED
        c['breakpoint_address'][self.id] = addr

    @property
    def status(self):
        c = self.debugger.debug_cmd[0]
        return c['breakpoint_status'][self.id]

    @status.setter
    def status(self, status):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = status

    def clear(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_EMPTY

    def enable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_ENABLED

    def disable(self):
        c = self.debugger.debug_cmd[0]
        c['breakpoint_status'][self.id] = dd.BREAKPOINT_DISABLED


class Watchpoint:
    def __init__(self, debugger, id, addr=None):
        self.debugger = debugger
        self.id = id


class Debugger:
    def __init__(self):
        self.debug_cmd_raw = np.zeros([dd.DEBUGGER_COMMANDS_DTYPE.itemsize], dtype=np.uint8)
        self.debug_cmd = self.debug_cmd_raw.view(dtype=dd.DEBUGGER_COMMANDS_DTYPE)

    def clear_all_breakpoints(self):
        c = self.debug_cmd[0]
        c['breakpoint_status'][:] = 0
        c['num_breakpoints'] = 0

    def create_breakpoint(self, addr=None):
        c = self.debug_cmd[0]
        empty = np.where(c['breakpoint_status'] == 0)[0]
        bpid = empty[0]
        if bpid >= c['num_breakpoints']:
            c['num_breakpoints'] = bpid + 1
        return Breakpoint(self, bpid, addr)

    def get_breakpoint(self, bpid):
        return Breakpoint(self, bpid)

    def get_watchpoint(self, bpid):
        return Watchpoint(self, bpid)
