import numpy as np
cimport numpy as np

np.import_array()  # needed to use np.PyArray_* functions

from libc.stdlib cimport free

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

cdef extern:
    int lib6502_init_cpu(int, int)
    int lib6502_cold_start(np.uint32_t *buf)
    int lib6502_next_frame(np.uint8_t *buf)
    np.uint32_t *lib6502_copy_op_history()
    void lib6502_fill_current_state(np.uint8_t *buf)
    np.uint32_t *lib6502_export_frame()
    void lib6502_import_frame(np.uint32_t *buf)
    void lib6502_set_a2_emulation_mode(np.uint8_t value)

def init_emulator(args):
    lib6502_init_cpu(262, 65)  # apple 2 speed

def cold_start(np.ndarray input = None):
    cdef np.uint32_t[:] ibuf
    cdef np.uint32_t *ibuf_addr

    if input is None:
        ibuf_addr = NULL
    else:
        ibuf = input.view(np.uint32)
        ibuf_addr = &ibuf[0]
    lib6502_cold_start(ibuf_addr)

def next_frame(np.ndarray input):
    cdef np.uint8_t[:] ibuf
    cdef np.uint8_t *ibuf_addr

    if input is None:
        ibuf_addr = NULL
    else:
        ibuf = input.view(np.uint8)
        ibuf_addr = &ibuf[0]
    result = lib6502_next_frame(ibuf_addr)
    return result

def export_op_history():
    cdef np.uint32_t *obuf

    obuf = lib6502_copy_op_history()
    count = obuf[0] // 4  # number of uint32 elements in array
    print(f"export_op_history: allocated={obuf[0]}, records:{obuf[2]} of {obuf[3]}, lookup: {obuf[4]} of {obuf[5]}")
    for i in range(20):
        print(f"{obuf[i]:0x}")
    steps = array_from_ptr(obuf, count, np.NPY_UINT32)
    return steps

def export_frame():
    cdef np.uint32_t *obuf

    obuf = lib6502_export_frame()
    count = obuf[0] // 4  # number of uint32 elements in array
    state = array_from_ptr(obuf, count, np.NPY_UINT8)
    return state

def import_frame(np.ndarray state not None):
    cdef np.uint32_t[:] sbuf
    sbuf = state.view(np.uint32)
    print(sbuf)
    lib6502_import_frame(&sbuf[0])

def fill_current_state(np.ndarray state not None):
    cdef np.uint8_t[:] sbuf
    sbuf = state.view(np.uint8)
    lib6502_fill_current_state(&sbuf[0])

def set_a2_emulation_mode(int value):
    lib6502_set_a2_emulation_mode(value)
