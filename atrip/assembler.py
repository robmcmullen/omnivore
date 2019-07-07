import os
import time
import inspect
import pkg_resources

from . import errors

import logging
log = logging.getLogger(__name__)


class AssemblerResult:
    def __init__(self):
        self.timestamp = time.ctime()
        self.errors = []
        self.segments = []
        self.transitory_equates = {}
        self.equates = {}
        self.labels = {}

    def __bool__(self):
        return not bool(self.errors)


class Assembler:
    name = "<base>"
    ui_name = "<pretty name>"
    cpu = "<cpu>"

    comment_char = ";"
    origin = "*="
    data_byte = ".byte"
    data_byte_prefix = "$"
    data_byte_separator = ", "

    def __init__(self, verbose=False):
        self.verbose = verbose

    def assemble(self, source):
        result = AssemblerResult()
        result.errors = ["No assemblers found"]
        return result


_assemblers = None

_default_assembler = None

def _find_assemblers():
    assemblers = []
    for entry_point in pkg_resources.iter_entry_points('atrip.assemblers'):
        mod = entry_point.load()
        log.debug(f"find_assembler: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Assembler in obj.__mro__[1:]:
                log.debug(f"find_assemblers:   found assembler class {name}")
                assemblers.append(obj)
    return assemblers

def find_assemblers():
    global _assemblers

    if _assemblers is None:
        _assemblers = _find_assemblers()
    return _assemblers

def find_assembler_by_name(name):
    items = find_assemblers()
    for c in items:
        if c.text_type == name:
            return c()
    raise KeyError(f"Unknown assembler {name}")

def set_default_assembler(name):
    global _default_assembler

    # let KeyError propagate up to indicate unknown assembler
    asm = find_assembler_by_name(name)
    _default_assembler = asm

def get_default_assembler():
    global _default_assembler

    if _default_assembler is None:
        find_assemblers()
        if len(_assemblers) == 0:
            _default_assembler = Assembler()
        elif len(_assemblers) == 1:
            _default_assembler = _assemblers[0]()
    return _default_assembler
