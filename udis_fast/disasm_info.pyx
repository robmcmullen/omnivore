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
    cdef public np.ndarray index
    cdef CurrentRow current
    cdef int itemsize
    cdef unsigned char *metadata_raw
    cdef char *instructions_raw

    def __init__(self, wrapper, first_pc, num_bytes):
        self.first_pc = first_pc
        self.num_bytes = num_bytes
        self.metadata, self.instructions, self.labels, self.index = wrapper.metadata_wrapper.copy_resize(num_bytes)
        self.num_instructions = len(self.metadata)
        self.itemsize = self.metadata.itemsize

        self.metadata_raw = <unsigned char *>self.metadata.data
        self.instructions_raw = self.instructions.data
        self.current = CurrentRow()

    def __len__(self):
        return self.num_instructions

    def __getitem__(self, int index):
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
        #     unsigned char strlen;
        #     unsigned char reserved;
        #     int strpos; /* position of start of text in instruction array */
        # } asm_entry;

        if index < 0 or index >= self.num_instructions:
            raise IndexError("Index %d invalid; number of instructions = %d" % (index, self.num_instructions))

        m = self.metadata_raw + (index * self.itemsize)
        sptr = <unsigned short *>m
        self.current.pc = sptr[0]
        self.current.dest_pc = sptr[1]
        self.current.num_bytes = m[4]
        self.current.flag = m[5]
        strlen = m[6]
        iptr = <int *>(m + 8)
        strpos = iptr[0]

        self.current.instruction = self.instructions_raw[strpos:strpos + strlen]
        return self.current

