from __future__ import division
import cython
import numpy as np
cimport numpy as np

# class DisassemblyRow(object):
#     def __init__(self, info, row):
#         data = info.metadata[row]
#         self.pc = data['pc']
#         start = data['strpos']
#         strlen = data['strlen']
#         end = start + strlen
#         self.instruction = info.instructions[start:end].view('S%d' % strlen)[0]
#         self.flag = data['flag']
#         self.num_bytes = data['count']
#         self.dest_pc = data['dest_pc']

cdef class CurrentRow:
    cdef public int pc
    cdef public int dest_pc
    cdef public bytes instruction
    cdef public int num_bytes
    cdef public int flag

cdef class DisassemblyInfo:
    cdef public int pc
    cdef public int first_pc
    cdef public int num_bytes
    cdef public int num_instructions
    cdef public np.ndarray metadata
    cdef public np.ndarray instructions
    cdef public np.ndarray labels
    cdef public np.ndarray index_to_row
    cdef CurrentRow current
    cdef int itemsize
    cdef unsigned char *metadata_raw
    cdef char *instructions_raw

    def __init__(self, wrapper, first_pc, num_bytes):
        self.first_pc = first_pc
        self.num_bytes = num_bytes
        self.metadata, self.instructions, self.labels, self.index_to_row = wrapper.metadata_wrapper.copy_resize(num_bytes)
        self.num_instructions = len(self.metadata)
        self.itemsize = self.metadata.itemsize

        self.metadata_raw = <unsigned char *>self.metadata.data
        self.instructions_raw = self.instructions.data
        self.current = CurrentRow()
        self.fix_offset_labels()
        wrapper.info = self  # update the info object in the wrapper

    def __len__(self):
        return self.num_instructions

    def __getitem__(self, int row):
        cdef char *text
        cdef unsigned char *m
        cdef unsigned short *sptr
        cdef int *iptr
        cdef int strlen
        cdef int strpos
        # Don't know how to reference this structure yet!
        # /* 12 byte structure */
        # typedef struct {
        #     unsigned short pc;
        #     unsigned short dest_pc; /* address pointed to by this opcode; if applicable */
        #     unsigned char count;
        #     unsigned char flag;
        #     unsigned short strlen;
        #     int strpos; /* position of start of text in instruction array */
        # } asm_entry;

        if row < 0 or row >= self.num_instructions:
            raise IndexError("Row %d invalid; number of instructions = %d" % (row, self.num_instructions))

        m = self.metadata_raw + (row * self.itemsize)
        sptr = <unsigned short *>m
        self.current.pc = sptr[0]
        self.current.dest_pc = sptr[1]
        self.current.num_bytes = m[4]
        self.current.flag = m[5]
        strlen = sptr[3]
        iptr = <int *>(m + 8)
        strpos = iptr[0]

        self.current.instruction = self.instructions_raw[strpos:strpos + strlen]
        return self.current

    def get_instruction_start_pc(self, int pc):
        cdef int index = pc - self.first_pc

        if index < 0 or index >= self.num_bytes:
            raise IndexError("PC %d out of range: %d - %d" % (pc, self.first_pc, self.first_pc + self.num_bytes))

        cdef int row = self.index_to_row[index]
        cdef unsigned char *m
        cdef unsigned short *sptr

        m = self.metadata_raw + (row * self.itemsize)
        sptr = <unsigned short *>m
        pc = sptr[0]
        return pc

    cdef fix_offset_labels(self):
        # fast loop in C to check for references to addresses that are in the
        # middle of an instruction. If found, a label is generated at the first
        # byte of the instruction
        cdef int pc = self.first_pc
        cdef int i = self.num_bytes
        cdef np.uint16_t *labels = <np.uint16_t *>self.labels.data
        cdef np.uint32_t *index_to_row = <np.uint32_t *>self.index_to_row.data

        #print "pc=%04x, last=%04x, i=%04x" % (pc, pc + i, i)
        while i > 0:
            i -= 1
            if labels[pc + i]:
                #print "disasm_info: found label %04x, index_to_row[%04x]=%04x" % (pc + i, i, index_to_row[i])
                while index_to_row[i - 1] == index_to_row[i] and i > 1:
                    i -= 1
                #if labels[pc + i] == 0:
                #    print "  disasm_info: added label at %04x" % (pc + i)
                labels[pc + i] = 1

cdef int data_style = 1

@cython.boundscheck(False)
@cython.wraparound(False)
def fast_disassemble_segment(disassembly_wrapper, segment, split_comments=[data_style]):
    cdef int i
    cdef np.uint8_t s, s2
    cdef int user_bit_mask = 0x7
    cdef int comment_bit_mask = 0x40
    cdef np.uint8_t c_split_comments[8]
    for i in range(8):
        c_split_comments[i] = 1 if i in split_comments else 0

    cdef np.ndarray style_copy = segment.get_comment_locations(user=user_bit_mask)
    cdef np.uint8_t *c_style = <np.uint8_t *>style_copy.data
    cdef num_bytes = min(len(style_copy), disassembly_wrapper.max_bytes)

    cdef int start_addr = segment.start_addr
    cdef int end_addr = start_addr + len(segment)
    cdef int pc = start_addr

    disassembly_wrapper.clear()
    if num_bytes < 1:
        return DisassemblyInfo(disassembly_wrapper, pc, 0)
    cdef int first_index = 0
    cdef int base_style = c_style[0] & user_bit_mask
    cdef int start_index, end_index, chunk_type
    # print "CYTHON FAST_GET_ENTIRE", style_copy
    ranges = []
    for i in range(1, num_bytes):
        s = style_copy[i]
        s2 = s & user_bit_mask
        # print "%04x" % i, s, s2,
        if s & comment_bit_mask:
            if s2 == base_style and not c_split_comments[s2]:
                # print "same w/skippable comment"
                continue
        elif s2 == base_style:
            # print "same"
            continue

        # process chuck here:
        start_index = first_index
        end_index = i
        chunk_type = base_style
        # print "last\nbreak here -> %x:%x = %s" % (start_index, end_index, chunk_type)
        processor = disassembly_wrapper.chunk_type_processor.get(chunk_type, disassembly_wrapper.chunk_processor)
        processor(disassembly_wrapper.metadata_wrapper, segment.rawdata.unindexed_data, pc + start_index, pc + end_index, start_index, disassembly_wrapper.mnemonic_lower , disassembly_wrapper.hex_lower)

        first_index = i
        base_style = s2

    # process last chunk
    start_index = first_index
    end_index = i + 1
    chunk_type = base_style
    processor = disassembly_wrapper.chunk_type_processor.get(chunk_type, disassembly_wrapper.chunk_processor)
    processor(disassembly_wrapper.metadata_wrapper, segment.rawdata.unindexed_data, pc + start_index, pc + end_index, start_index, disassembly_wrapper.mnemonic_lower , disassembly_wrapper.hex_lower)

    return DisassemblyInfo(disassembly_wrapper, pc, num_bytes)
