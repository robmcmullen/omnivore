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

from flags import *

import logging
log = logging.getLogger(__name__)


class StorageWrapper(object):
    def __init__(self, lines=65536, strsize=12):
        # string array
        self.metadata = np.empty((lines,), dtype="|S%d" % strsize)
        self.row = 0
        self.num_rows = self.metadata.shape[0]
        self.strsize = self.metadata.itemsize
        self.labels = np.zeros([256*256], dtype=np.uint16)
        self.index_to_row = np.zeros([256*256], dtype=np.uint32)
        self.max_strpos = 2000000
        self.instructions = np.empty([self.max_strpos], dtype='S1')
        self.last_strpos = 0

        # strings are immutable, so get a view of bytes that we can change
        self.data = self.metadata.view(dtype=np.uint8).reshape((self.num_rows, self.strsize))
        self.clear()

    def clear(self):
        self.data[:,:] = ord(" ")
        self.labels[:] = 0
        self.index_to_row[:] = 0
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
        index = np.empty([num_bytes], dtype=self.index_to_row.dtype)
        index[:] = self.index_to_row[:num_bytes]
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
        self.metadata, self.instructions, self.labels, self.index_to_row = wrapper.metadata_wrapper.copy_resize(num_bytes)
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

def get_disassembler(cpu, fast=True, monolithic=True):
    if cpu == "dev":
        import disasm_speedups_dev
        processor = functools.partial(disasm_speedups_dev.get_disassembled_chunk_fast, cpu)
        strsize = 12
        return processor, cpu, strsize
    if monolithic:
        import disasm_speedups_monolithic
        processor = functools.partial(disasm_speedups_monolithic.get_disassembled_chunk_fast, cpu)
        strsize = 12
        return processor, cpu, strsize
    try:
        if not fast:
            raise RuntimeError
        mod_name = "udis_fast.disasm_speedups_%s" % cpu
        try:
            parse_mod = importlib.import_module(mod_name)
        except ImportError:
            mod_name = "udis.udis_fast.disasm_speedups_%s" % cpu
            parse_mod = importlib.import_module(mod_name)
        processor = parse_mod.get_disassembled_chunk_fast
        strsize = 12
    except RuntimeError:
        mod_name = "udis_fast.hardcoded_parse_%s" % cpu
        parse_mod = importlib.import_module(mod_name)
        processor = functools.partial(get_disassembled_chunk, parse_mod)
        strsize = 48
    return processor, parse_mod, strsize


class TraceInfo(object):
    def __init__(self, num_bytes=65536):
        self.seen = np.zeros([num_bytes], dtype=np.uint8)
        self.start_points = set()
        self.out_of_range_start_points = set()
    
    def __len__(self):
        return len(self.seen)

    def __getitem__(self, index):
        return self.seen[index]
    
    def __setitem__(self, index, value):
        self.seen[index] = value

    @property
    def marked_as_data(self):
        return 1 - self.seen


class DisassemblerWrapper(object):
    def __init__(self, cpu, lines=65536, fast=True, mnemonic_lower=False, hex_lower=True, extra_disassemblers=None, monolithic=True):
        self.max_bytes = 65536
        processor, parse_mod, strsize = get_disassembler(cpu, fast, monolithic)
        self.fast = fast
        self.monolithic = monolithic
        self.chunk_processor = processor
        self.metadata_wrapper = StorageWrapper(lines, strsize)
        self.mnemonic_lower = mnemonic_lower
        self.hex_lower = hex_lower
        if extra_disassemblers is None:
            extra_disassemblers = {}
        self.chunk_type_processor = extra_disassemblers
        # default chunk processor is the normal disassembler
        self.chunk_type_processor[0] = self.chunk_processor
        self.info = None

    def add_chunk_processor(self, cpu, chunk_type):
        self.chunk_type_processor[chunk_type] = get_disassembler(cpu, self.fast, self.monolithic)[0]

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

    def get_all(self, binary, pc, index_of_pc, ranges=[]):
        import disasm_info

        self.clear()
        # limit to 64k at once since we're dealing with 8-bit machines
        num_bytes = min(len(binary) - index_of_pc, self.max_bytes)
        if not ranges:
            ranges = [((0, num_bytes), 0)]
        last = False
        for (start_index, end_index), chunk_type in ranges:
            # get some fun segfaults if this isn't limited to 64k; it wraps
            # around some of the arrays, but steps over the boundary of others.
            # Bad stuff.
            if end_index > self.max_bytes:
                last = True
                end_index = self.max_bytes
            processor = self.chunk_type_processor.get(chunk_type, self.chunk_processor)
            processor(self.metadata_wrapper, binary, pc + start_index, pc + end_index, start_index, self.mnemonic_lower , self.hex_lower)
            if last:
                break
        self.info = disasm_info.DisassemblyInfo(self, pc, num_bytes)
        return self.info

    def find_callers(self, dest_pc):
        info = self.info
        records = info.metadata.view(dtype=rawdtype)
        row_with_dest_pc = np.where(records['dest_pc'] == dest_pc)[0]
        found = records['pc'][row_with_dest_pc]
        return found

    def trace_disassembly(self, trace_info, start_points):
        info = self.info
        stack = set(start_points)
        last_pc = info.first_pc + info.num_bytes
        pc_to_row = np.zeros([last_pc], dtype=np.uint32)
        pc_to_row[info.first_pc:] = info.index_to_row[:]

        # always start a trace when it's user specified to allow tracing of an
        # instruction that has its first byte marked as seen
        user_specified = set(start_points)

        def valid_pc(dest_pc):
            return dest_pc >= info.first_pc and dest_pc < last_pc

        while stack:
            pc = stack.pop()
            if pc < info.first_pc or pc >= last_pc:
                log.debug("skipping trace of %04x: not in disassembled range." % pc)
                trace_info.out_of_range_start_points.add(pc)
                continue
            if trace_info[pc] and pc not in user_specified:
                log.debug("skipping trace of %04x: already checked it" % pc)
                continue
            log.debug("starting trace at %04x" % pc)
            user_specified.discard(pc)
            trace_info.start_points.add(pc)
            first = True
            while pc < last_pc:
                if trace_info[pc] and not first:
                    break
                first = False
                row = pc_to_row[pc]
                line = info[row]
                if line.flag & flag_data_bytes:
                    log.debug("%04x: disassembled into marked data; moving to next entry point" % pc)
                    break
                next_pc = pc + line.num_bytes
                trace_info[pc:next_pc] = 1
                if line.dest_pc > 0:
                    if line.flag & flag_branch:
                        if not valid_pc(line.dest_pc):
                            log.debug("%04x: found branch to %04x, but not in disassembled range" % (pc, line.dest_pc))
                            trace_info.out_of_range_start_points.add(line.dest_pc)
                        elif trace_info[line.dest_pc]:
                            log.debug("%04x: found branch to %04x, but already checked it" % (pc, line.dest_pc))
                        elif line.dest_pc in stack:
                            log.debug("%04x: found branch to %04x, but already in list to be checked" % (pc, line.dest_pc))
                        else:
                            log.debug("%04x: found branch to %04x" % (pc, line.dest_pc))
                            stack.add(line.dest_pc)
                    if line.flag & flag_jump:
                        if not valid_pc(line.dest_pc):
                            log.debug("%04x: found jump to %04x, but not in disassembled range" % (pc, line.dest_pc))
                            trace_info.out_of_range_start_points.add(line.dest_pc)
                            break
                        elif trace_info[line.dest_pc]:
                            log.debug("%04x: found jump to %04x, but already checked it" % (pc, line.dest_pc))
                            break
                        log.debug("%04x: jumping to %04x" % (pc, line.dest_pc))
                        next_pc = line.dest_pc
                if line.flag & flag_return:
                    log.debug("%04x: end of this trace; moving to next entry point" % (pc))
                    break
                pc = next_pc
        log.debug(trace_info[info.first_pc:last_pc])
