# cython: language_level=3
from libc.stdio cimport printf
from libc.string cimport strstr, strcasestr
from libc.stdlib cimport free
import cython
import numpy as np
cimport numpy as np

np.import_array()  # needed to use np.PyArray_* functions



######################################################################
#
# Memory Utilities
#
######################################################################


# from https://stackoverflow.com/questions/23872946/force-numpy-ndarray-to-take-ownership-of-its-memory-in-cython/
from cpython.object cimport PyObject
from cpython.ref cimport Py_INCREF
cdef class MemoryNanny:
    cdef void* ptr # set to NULL by "constructor"
    def __dealloc__(self):
        print("freeing ptr=0x%x" % <unsigned long long>(self.ptr)) #just for debugging
        free(self.ptr)

    @staticmethod
    cdef create(void* ptr):
        cdef MemoryNanny result = MemoryNanny()
        result.ptr = ptr
        print("nanny for ptr=0x%x" % <unsigned long long>(result.ptr)) #just for debugging
        return result

cdef extern from "numpy/arrayobject.h":
    # a little bit awkward: the reference to obj will be stolen
    # using PyObject*  to signal that Cython cannot handle it automatically
    int PyArray_SetBaseObject(np.ndarray arr, PyObject *obj) except -1 # -1 means there was an error

cdef array_from_ptr(void * ptr, np.npy_intp N, int np_type):
    cdef np.ndarray arr = np.PyArray_SimpleNewFromData(1, &N, np_type, ptr)
    nanny = MemoryNanny.create(ptr)
    Py_INCREF(nanny) # a reference will get stolen, so prepare nanny
    PyArray_SetBaseObject(arr, <PyObject*>nanny)
    return arr









######################################################################
#
# 6502 Emulator
#
######################################################################

cdef extern:
    int lib6502_init_cpu(int, int)
    int lib6502_cold_start(np.uint32_t *buf)
    int lib6502_next_frame(np.uint8_t *buf, np.uint8_t *buf)
    np.uint32_t *lib6502_copy_op_history()
    void lib6502_fill_current_state(np.uint8_t *buf)
    np.uint32_t *lib6502_export_frame()
    void lib6502_import_frame(np.uint32_t *buf)
    int lib6502_eval_history(np.uint32_t *previous_frame, np.uint8_t *current, np.uint32_t *buf, int line_number)
    void lib6502_set_a2_emulation_mode(np.uint8_t value)

class Emu6502:
    def __init__(self, args):
        lib6502_init_cpu(262, 65)  # apple 2 speed

    def cold_start(self, np.ndarray input = None):
        cdef np.uint32_t[:] ibuf
        cdef np.uint32_t *ibuf_addr

        if input is None:
            ibuf_addr = NULL
        else:
            ibuf = input.view(np.uint32)
            ibuf_addr = &ibuf[0]
        lib6502_cold_start(ibuf_addr)

    def next_frame(self, np.ndarray user_input, np.ndarray mid_frame_input):
        cdef np.uint8_t[:] ibuf
        cdef np.uint8_t *ibuf_addr
        cdef np.uint8_t[:] mbuf
        cdef np.uint8_t *mbuf_addr

        if user_input is None:
            ibuf_addr = NULL
        else:
            ibuf = user_input.view(np.uint8)
            ibuf_addr = &ibuf[0]
        if mid_frame_input is None:
            mbuf_addr = NULL
        else: 
            mbuf = mid_frame_input.view(np.uint8)
            mbuf_addr = &mbuf[0]
        result = lib6502_next_frame(ibuf_addr, mbuf_addr)
        return result

    def export_op_history(self):
        cdef np.uint32_t *obuf_addr

        obuf_addr = lib6502_copy_op_history()
        count = obuf_addr[0] // 4  # number of uint32 elements in array
        print(f"export_op_history: allocated={obuf_addr[0]}, records:{obuf_addr[2]} of {obuf_addr[3]}, lookup: {obuf_addr[4]} of {obuf_addr[5]}")
        for i in range(20):
            print(f"{obuf_addr[i]:0x}")
        steps = array_from_ptr(obuf_addr, count, np.NPY_UINT32)
        return steps

    def export_frame(self):
        cdef np.uint32_t *obuf_addr

        obuf_addr = lib6502_export_frame()
        count = obuf_addr[0] // 4  # number of uint32 elements in array
        state = array_from_ptr(obuf_addr, count, np.NPY_UINT8)
        return state

    def import_frame(self, np.ndarray frame not None):
        cdef np.uint32_t[:] fbuf
        fbuf = frame.view(np.uint32)
        lib6502_import_frame(&fbuf[0])

    def fill_current_state(self, np.ndarray state not None):
        cdef np.uint8_t[:] sbuf
        sbuf = state.view(np.uint8)
        lib6502_fill_current_state(&sbuf[0])

    def eval_operation(self, np.ndarray frame not None, np.ndarray state not None, np.ndarray op_history not None, int line_number):
        cdef np.uint32_t[:] fbuf
        cdef np.uint8_t[:] sbuf
        cdef np.uint32_t[:] obuf

        fbuf = frame.view(np.uint32)
        sbuf = state.view(np.uint8)
        obuf = op_history.view(np.uint32)
        return lib6502_eval_history(&fbuf[0], &sbuf[0], &obuf[0], line_number)










######################################################################
#
# Crabapple Emulator
#
######################################################################

class EmuCrabapple(Emu6502):
    def __init__(self, args):
        lib6502_init_cpu(262, 65)  # apple 2 speed
        lib6502_set_a2_emulation_mode(1)













######################################################################
#
# Disassembler
#
######################################################################

OP_HISTORY_T_SIZE = 6

from libemu cimport op_record_t, op_history_t, jmp_targets_t

cdef extern:
    int disassemble(op_history_t *buf, int origin, int num_bytes, np.uint8_t *src, np.uint8_t *style, np.uint8_t *disasm_type, np.uint32_t *order, np.uint8_t *split_comments, jmp_targets_t *jmp_targets)
    op_history_t *create_op_history(int, int, int)


cdef char *hexdigits_lower = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff"
cdef char *hexdigits_upper = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF"

cdef int data_style = 0

cdef class DisassemblyConfig:
    cdef np.uint8_t c_split_comments[256]
    cdef np.uint8_t default_disasm_type
    cdef public np.ndarray jmp_targets
    cdef jmp_targets_t *jmp_targets_data

    def __init__(self, def_disasm_type=0, split_comments=[data_style]):
        cdef int i

        for i in range(256):
            self.c_split_comments[i] = 1 if i in split_comments else 0
        self.default_disasm_type = def_disasm_type
        self.op_history = None
        self.jmp_targets = np.zeros(sizeof(jmp_targets_t), dtype=np.uint8)
        self.jmp_targets_data = <jmp_targets_t *>self.jmp_targets.data

    def check_op_history(self, size):
        cdef np.uint32_t[:] obuf
        cdef np.uint32_t *obuf_addr

        requested = (size * 10, size, size)
        if self.op_history is not None:
            obuf = self.op_history.view(np.uint32)
            num_records = obuf[2]
            print(f"num_records: {num_records}")
            num_lines = obuf[4]
            print(f"num_records: {num_lines}")
            num_bytes = obuf[6]
            print(f"num_records: {num_bytes}")
            if num_records < requested[0] or num_lines < requested[1] or num_bytes < requested[2]:
                self.op_history = None
        if self.op_history is None:
            obuf_addr = <np.uint32_t *>create_op_history(requested[0], requested[1], requested[2])
            count = obuf_addr[0] // 4  # number of uint32 elements in array
            arr = array_from_ptr(obuf_addr, count, np.NPY_UINT32)
            self.op_history = arr

    def parse(self, segment, num_entries):
        cdef np.ndarray[np.uint8_t, ndim=1] src_copy = segment.container._data
        cdef np.uint8_t *c_src = <np.uint8_t *>src_copy
        cdef np.ndarray[np.uint8_t, ndim=1] style_copy = segment.container._style
        cdef np.uint8_t *c_style = <np.uint8_t *>style_copy
        cdef np.ndarray[np.uint8_t, ndim=1] disasm_type_copy = segment.container._disasm_type
        cdef np.uint8_t *c_disasm_type = <np.uint8_t *>disasm_type_copy
        cdef np.ndarray[np.uint32_t, ndim=1] order_copy = segment.container_offset
        cdef np.uint32_t *c_order = <np.uint32_t *>order_copy.data
        cdef int num_bytes = len(order_copy)

        self.check_op_history(num_bytes)

        cdef int origin = segment.origin
        cdef int end_addr = origin + num_bytes
        cdef int pc = origin
        cdef int processed_bytes
        cdef np.ndarray[np.uint32_t, ndim=1] op_h = self.op_history
        cdef op_history_t *obuf_addr = <op_history_t *>&op_h[0]

        processed_bytes = disassemble(obuf_addr, origin, num_bytes, c_src, c_style, c_disasm_type, c_order, &self.c_split_comments[0], self.jmp_targets_data)
        print(f"processed_bytes: {processed_bytes}")
