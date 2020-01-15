import numpy as np
cimport numpy as np

cdef extern:
    int lib6502_init_cpu(int, int)
    int lib6502_cold_start(np.uint32_t *buf)
    int lib6502_next_frame(np.uint8_t *buf)
    np.uint32_t *lib6502_export_steps()
    np.uint8_t *lib6502_export_frame()
    void lib6502_import_frame(np.uint8_t *buf)
    void lib6502_set_a2_emulation_mode(np.uint8_t value)

def init_emulator(args):
    lib6502_init_cpu(262, 65)  # apple 2 speed

def cold_start(np.ndarray input not None):
    cdef np.uint32_t[:] ibuf

    ibuf = input.view(np.uint32)
    lib6502_cold_start(&ibuf[0])

def next_frame(np.ndarray input not None):
    cdef np.uint8_t[:] ibuf  # ignored for this emulator

    ibuf = input.view(np.uint8)
    result = lib6502_next_frame(&ibuf[0])
    return result

def export_steps():
    cdef np.uint32_t *obuf

    obuf = lib6502_export_steps()
    count = obuf[0]  # number of uint32 elements in array
    steps = np.PyArray_SimpleNewFromData(1, [count], np.NPY_UINT32, obuf)
    np.PyArray_ENABLEFLAGS(steps, np.NPY_OWNDATA)
    return steps

def export_frame():
    cdef np.uint8_t *obuf

    obuf = lib6502_export_frame()
    count = obuf[0]  # number of uint8 elements in array
    state = np.PyArray_SimpleNewFromData(1, [count], np.NPY_UINT8, obuf)
    np.PyArray_ENABLEFLAGS(state, np.NPY_OWNDATA)
    return state

def import_frame(np.ndarray state not None):
    cdef np.uint8_t[:] sbuf
    sbuf = state.view(np.uint8)
    lib6502_import_frame(&sbuf[0])

def set_a2_emulation_mode(int value):
    lib6502_set_a2_emulation_mode(value)
