import os
import time
import inspect
import pkg_resources

from . import errors

from atrip.memory_map import size_codes

import logging
log = logging.getLogger(__name__)


class DataInfo:
    def __init__(self, label, addr, type_code, count):
        self.label = label
        self.addr = addr
        self.type_code = type_code
        self.count = count
        self.byte_count = self.count * (size_codes[type_code] + 1)

    def __str__(self):
        return f"DataInfo: {self.label}@${self.addr:04x}, {self.count}x{self.type_code}"

    def __repr__(self):
        return f"DataInfo: {self.label}@${self.addr:04x}, {self.count}x{self.type_code}"


class AssemblerResult:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.timestamp = time.ctime()
        self.errors = []
        self.segments = []
        self.transitory_equates = {}
        self.equates = {}
        self.labels = {}
        self.data_info = {}
        self.addr_to_label = {}
        self.addr_type_code = {}
        self.first_addr = None
        self.last_addr = None
        self.current_bytes = []
        self.user_variable_labels = None

    def __bool__(self):
        return not bool(self.errors)

    def add_label(self, label, addr):
        label = label.lower()
        addr = int(addr, 16)
        self.labels[label] = addr
        if addr not in self.addr_to_label:
            # first label takes priority if multiple labels for same addr
            self.addr_to_label[addr] = label

    def generate_data_info(self):
        assembled_addrs = sorted(self.addr_type_code.keys())
        print(assembled_addrs)
        print(self.addr_to_label)
        if len(assembled_addrs) < 1:
            return

        index = 0
        self.data_info = {}
        current_info = None

        def add_data(info):
            if self.verbose: print(f"adding data info: {info}")
            self.data_info[info.label] = info

        try:
            while True:
                if current_info is None:
                    # find label
                    while True:
                        start = assembled_addrs[index]
                        try:
                            label = self.addr_to_label[start]
                            current_type_code = self.addr_type_code[start]
                            if current_type_code == "code":
                                raise KeyError(f"address type_code {current_type_code} is not data")
                            current_info = DataInfo(label, start, current_type_code, 1)
                        except KeyError as e:
                            print(f"index={index}: start={start:x}, {e}")
                            index += 1
                        else:
                            break

                # when we get here, we have a label that is pointing to some
                # data, so find next label, gap in addresses assembled, or
                # change in data type_code
                if self.verbose: print(f"found data info: {current_info}")
                last = start
                while True:
                    index += 1
                    print(f"trying {index:x}")
                    end = assembled_addrs[index]
                    print(f"found {end:x} at {index}")
                    if end > start + current_info.count + 1:
                        # gap in addresses, meaning the data block has ended
                        add_data(current_info)
                        current_info = None
                        break
                    elif end in self.addr_to_label or self.addr_type_code[end] != current_type_code:
                        add_data(current_info)
                        current_info = None
                        break
                    else:
                        current_info.count += 1
        except IndexError:
            # no more addresses in assembled_addrs array
            if self.verbose: print(f"finished processing assembled_addrs")
            if current_info is not None:
                add_data(current_info)
        if self.verbose: print(self.data_info)

    def find_next_address_with_label(self, addr):
        for a in sorted(self.addr_to_label):
            if a > addr:
                break
        else:
            raise KeyError
        return a


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
