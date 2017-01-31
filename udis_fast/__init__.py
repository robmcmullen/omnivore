import importlib
import functools

import numpy as np

class StorageWrapper(object):
    def __init__(self, lines=1000):
        # string array
        self.storage = np.empty((lines,), dtype="|S48")
        self.row = 0
        self.num_rows = self.storage.shape[0]
        self.strsize = self.storage.itemsize
        self.labels = np.zeros([256*256], dtype=np.uint16)

        # strings are immutable, so get a view of bytes that we can change
        self.data = self.storage.view(dtype=np.uint8).reshape((self.num_rows, self.strsize))
        self.clear()

    def clear(self):
        self.data[:,:] = ord(" ")
        self.row = 0

    def __getitem__(self, index):
        return self.data[self.row, index]
    
    def __setitem__(self, index, value):
        self.data[self.row, index] = value

    def next(self):
        self.row += 1
        if self.row == self.num_rows:
            return False
        return True

def get_disassembled_chunk(parse_mod, storage_wrapper, binary, pc, last, index_of_pc):
    while pc < last:
        count = parse_mod.parse_instruction_numpy(storage_wrapper, pc, binary[index_of_pc:index_of_pc+4], last)
        if count > 0:
            pc += count
            index_of_pc += count
            if not storage_wrapper.next():
                break
        else:
            break
    return pc, index_of_pc


class DisassemblerWrapper(object):
    def __init__(self, cpu, fast=True):
        self.disasm = self.get_disassembler(cpu, fast)
        self.storage_wrapper = StorageWrapper(1000)

    def get_disassembler(self, cpu, fast=True):
        try:
            if not fast:
                raise RuntimeError
            mod_name = "udis_fast.disasm_speedups_%s" % cpu
            parse_mod = importlib.import_module(mod_name)
            self.chunk_processor = parse_mod.get_disassembled_chunk_fast
        except RuntimeError:
            mod_name = "udis_fast.hardcoded_parse_%s" % cpu
            parse_mod = importlib.import_module(mod_name)
            self.chunk_processor = functools.partial(get_disassembled_chunk, parse_mod)
        return parse_mod

    @property
    def rows(self):
        return self.storage_wrapper.row

    @property
    def labels(self):
        return self.storage_wrapper.labels

    @property
    def storage(self):
        return self.storage_wrapper.storage
    
    
    def clear(self):
        self.storage_wrapper.clear()

    def next_chunk(self, binary, pc, last, i):
        return self.chunk_processor(self.storage_wrapper, binary, pc, last, i)
