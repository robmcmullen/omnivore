from libc.stdlib cimport malloc, free
import numpy as np
cimport numpy as np

cdef extern:
    int a8bridge_init(int, char **)
    void a8bridge_clear_state_arrays(void *input, void *output)
    void a8bridge_configure_state_arrays(void *input, void *output)
    void a8bridge_get_current_state(void *output)
    void a8bridge_restore_state(void *restore)
    int a8bridge_next_frame(void *input, void *output, void *breakpoints, void *history)
    void a8bridge_show_next_instruction(void *history)

    int libatari800_mount_disk_image(int diskno, const char *filename, int readonly)
    int libatari800_reboot_with_file(const char *filename)


cdef char ** to_cstring_array(list_str):
    cdef char **ret = <char **>malloc(len(list_str) * sizeof(char *))
    for i in xrange(len(list_str)):
        text = list_str[i].encode()
        ret[i] = text
    return ret

def start_emulator(args):
    cdef char *fake_args[10]
    cdef char **argv = fake_args
    cdef int argc
    cdef int err
    cdef char *progname="pyatari800"
    cdef char **c_args = to_cstring_array(args)

    argc = 1
    fake_args[0] = progname
    for i in xrange(len(args)):
        arg = c_args[i]
        fake_args[argc] = arg
        argc += 1

    err = a8bridge_init(argc, argv)
    if err != 1:
        raise RuntimeError(f"Failed starting emulator: error code {err}")
    free(c_args)

def clear_state_arrays(np.ndarray input not None, np.ndarray output not None):
    cdef np.uint8_t[:] ibuf
    cdef np.uint8_t[:] obuf

    ibuf = input.view(np.uint8)
    obuf = output.view(np.uint8)
    a8bridge_clear_state_arrays(&ibuf[0], &obuf[0])

def configure_state_arrays(np.ndarray input not None, np.ndarray output not None):
    cdef np.uint8_t[:] ibuf
    cdef np.uint8_t[:] obuf

    ibuf = input.view(np.uint8)
    obuf = output.view(np.uint8)
    a8bridge_configure_state_arrays(&ibuf[0], &obuf[0])

def next_frame(np.ndarray input not None, np.ndarray output not None, np.ndarray breakpoints not None, history_storage):
    cdef np.uint8_t[:] ibuf
    cdef np.uint8_t[:] obuf
    cdef np.uint8_t[:] dbuf
    cdef np.uint8_t *hbuf
    cdef np.uint8_t[:] tmp
    if history_storage is not None:
        tmp = history_storage.history_array.view(np.uint8)
        hbuf = &tmp[0]
    else:
        hbuf = <np.uint8_t *>0

    ibuf = input.view(np.uint8)
    obuf = output.view(np.uint8)
    dbuf = breakpoints.view(np.uint8)
    bpid = a8bridge_next_frame(&ibuf[0], &obuf[0], &dbuf[0], hbuf)
    return bpid

def show_next_instruction(history_storage):
    cdef np.uint8_t *hbuf
    cdef np.uint8_t[:] tmp
    if history_storage is not None:
        tmp = history_storage.history_array.view(np.uint8)
        hbuf = &tmp[0]
    else:
        hbuf = <np.uint8_t *>0
    a8bridge_show_next_instruction(hbuf)

def get_current_state(np.ndarray output not None):
    cdef np.uint8_t[:] obuf

    obuf = output.view(np.uint8)
    a8bridge_get_current_state(&obuf[0])

def load_disk(int disknum, pathname, int readonly=0):
    filename = pathname.encode('utf-8')
    libatari800_mount_disk_image(disknum, filename, readonly)

def reboot_with_file(pathname):
    filename = pathname.encode('utf-8')
    libatari800_reboot_with_file(filename)

def restore_state(np.ndarray state not None):
    cdef np.uint8_t[:] sbuf
    sbuf = state.view(np.uint8)
    a8bridge_restore_state(&sbuf[0])
