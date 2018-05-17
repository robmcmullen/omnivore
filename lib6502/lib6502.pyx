import numpy as np
cimport numpy as np

cdef extern:
    int init_cpu()
    int step_cpu(int)
    long next_frame(long)
    void get_current_state(void *buf)
    void restore_state(void *buf)

def start_emulator(args, python_callback_function, python_callback_args):
    init_cpu()

def prepare_arrays(np.ndarray input not None, np.ndarray output not None):
    return

def next_frame(np.ndarray input not None, np.ndarray output not None):
    cdef np.uint8_t[:] ibuf
    cdef np.uint8_t[:] obuf

    ibuf = input.view(np.uint8)
    obuf = output.view(np.uint8)
    next_frame(&ibuf[0], &obuf[0])
    load_state(&obuf[0])

def get_current_state(np.ndarray output not None):
    cdef np.uint8_t[:] obuf

    obuf = output.view(np.uint8)
    get_current_state(&obuf[0])

def load_disk(int disknum, char *filename, int readonly=0):
    raise NotImplementedError

def restore_state(np.ndarray state not None):
    cdef np.uint8_t[:] sbuf
    sbuf = state.view(np.uint8)
    restore_state(&sbuf[0])

def monitor_step(int addr=-1):
    cdef int resume;
    resume = step_cpu(0)
    return resume

def monitor_summary():
    raise NotImplementedError

def monitor_clear():
    raise NotImplementedError
