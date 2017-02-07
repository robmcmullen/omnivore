import importlib
import functools

import numpy as np

# mimicking the 12 byte C structure:
# 
# /* 12 byte structure */
# typedef struct {
#     unsigned short pc;
#     unsigned short dest_pc; /* address pointed to by this opcode; if applicable */
#     unsigned char count;
#     unsigned char flag;
#     unsigned char strlen;
#     unsigned char reserved;
#     int strpos; /* position of start of text in instruction array */
# } asm_entry;

rawdtype = [('pc', 'u2'), ('dest_pc', 'u2'), ('count', 'u1'), ('flag', 'u1'), ('strlen', 'u1'), ('unused', 'u1'), ('strpos', 'i4')]

class StorageWrapper(object):
    def __init__(self, lines=65536, strsize=12):
        # string array
        self.metadata = np.empty((lines,), dtype="|S%d" % strsize)
        self.row = 0
        self.num_rows = self.metadata.shape[0]
        self.strsize = self.metadata.itemsize
        self.labels = np.zeros([256*256], dtype=np.uint16)
        self.index = np.zeros([256*256], dtype=np.uint32)
        self.max_strpos = 2000000
        self.instructions = np.empty([self.max_strpos], dtype='S1')
        self.last_strpos = 0

        # strings are immutable, so get a view of bytes that we can change
        self.data = self.metadata.view(dtype=np.uint8).reshape((self.num_rows, self.strsize))
        self.clear()

    def clear(self):
        self.data[:,:] = ord(" ")
        self.labels[:] = 0
        self.index[:] = 0
        self.row = 0
        self.last_strpos = 0

    def __getitem__(self, index):
        return self.data[self.row, index]
    
    def __setitem__(self, index, value):
        self.data[self.row, index] = value

    def next(self):
        self.row += 1
        if self.row == self.num_rows:
            return False
        return True

    def view(self, row):
        return self.metadata.view(dtype=rawdtype)[row]

    def copy_resize(self, num_bytes):
        count = self.row
        metadata = np.empty([count], dtype=rawdtype)
        m = metadata.view(dtype=np.uint8).reshape([count, self.strsize])
        m[:] = self.data[:count]
        text = np.empty([self.last_strpos], dtype='S1')
        text[:] = self.instructions[:self.last_strpos]
        labels = np.empty([self.labels.shape[0]], dtype=self.labels.dtype)
        labels[:] = self.labels[:]
        index = np.empty([num_bytes], dtype=self.index.dtype)
        index[:] = self.index[:num_bytes]
        return metadata, text, labels, index

class SlowDisassemblyRow(object):
    def __init__(self, info, row):
        data = info.metadata[row]
        self.pc = data['pc']
        start = data['strpos']
        strlen = data['strlen']
        end = start + strlen
        self.instruction = info.instructions[start:end].view('S%d' % strlen)[0]
        self.flag = data['flag']
        self.num_bytes = data['count']
        self.dest_pc = data['dest_pc']

class SlowDisassemblyInfo(object):
    def __init__(self, wrapper, first_pc, num_bytes):
        self.first_pc = first_pc
        self.num_bytes = num_bytes
        self.metadata, self.instructions, self.labels, self.index = wrapper.metadata_wrapper.copy_resize(num_bytes)
        self.num_instructions = len(self.metadata)

    def __getitem__(self, index):
        return DisassemblyRow(self, index)

    def print_instructions(self, start, count):
        for i in range(start, start+count):
            data = self[i]
            line = "%d %s" % (data.pc, data.instruction)
            print line


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

def get_disassembler(cpu, fast=True):
    try:
        if not fast:
            raise RuntimeError
        mod_name = "udis_fast.disasm_speedups_%s" % cpu
        parse_mod = importlib.import_module(mod_name)
        processor = parse_mod.get_disassembled_chunk_fast
        strsize = 12
    except RuntimeError:
        mod_name = "udis_fast.hardcoded_parse_%s" % cpu
        parse_mod = importlib.import_module(mod_name)
        processor = functools.partial(get_disassembled_chunk, parse_mod)
        strsize = 48
    return processor, parse_mod, strsize

import disasm_info
import disasm_speedups_data
import disasm_speedups_antic_dl

class DisassemblerWrapper(object):
    def __init__(self, cpu, lines=65536, fast=True, mnemonic_lower=False, hex_lower=True, extra_disassemblers=None):
        processor, parse_mod, strsize = get_disassembler(cpu, fast)
        self.chunk_processor = processor
        self.metadata_wrapper = StorageWrapper(lines, strsize)
        self.mnemonic_lower = mnemonic_lower
        self.hex_lower = hex_lower
        if extra_disassemblers is None:
            extra_disassemblers = {}
        self.chunk_type_processor = extra_disassemblers
        # default chunk processor is the normal disassembler
        self.chunk_type_processor[0] = self.chunk_processor

    def add_data_processor(self, chunk_type):
        self.chunk_type_processor[chunk_type] = disasm_speedups_data.get_disassembled_chunk_fast

    def add_antic_dl_processor(self, chunk_type):
        self.chunk_type_processor[chunk_type] = disasm_speedups_antic_dl.get_disassembled_chunk_fast

    @property
    def rows(self):
        return self.metadata_wrapper.row

    @property
    def labels(self):
        return self.metadata_wrapper.labels

    @property
    def storage(self):
        return self.metadata_wrapper.metadata
    
    
    def clear(self):
        self.metadata_wrapper.clear()

    def next_chunk(self, binary, pc, last, i):
        return self.chunk_processor(self.metadata_wrapper, binary, pc, last, i, self.mnemonic_lower , self.hex_lower)

    def get_all(self, binary, pc, i, ranges=[]):
        self.clear()
        # limit to 64k at once since we're dealing with 8-bit machines
        num_bytes = min(len(binary) - i, 65536)
        if not ranges:
            ranges = [((0, num_bytes), 0)]
        last = False
        for (start_index, end_index), chunk_type in ranges:
            # get some fun segfaults if this isn't limited to 64k; it wraps
            # around some of the arrays, but steps over the boundary of others.
            # Bad stuff.
            if end_index > 65536:
                last = True
                end_index = 65536
            processor = self.chunk_type_processor.get(chunk_type, self.chunk_processor)
            processor(self.metadata_wrapper, binary, pc + start_index, pc + end_index, start_index, self.mnemonic_lower , self.hex_lower)
            if last:
                break
        info = disasm_info.DisassemblyInfo(self, pc, num_bytes)
        return info
