from libc.stdlib cimport malloc, free
from cpython.string cimport PyString_AsString
import ctypes

ctypedef void (*c_cb_ptr)(unsigned char *)

cdef extern:
    int start_shmem(void *, int, c_cb_ptr)
    void SHMEM_Debug4k(unsigned char *)

pycallback = None

cdef void callback(unsigned char *mem):
    py_mem = mem[0:256*256]
    ptr = mem
    print "in cython callback"
    SHMEM_Debug4k(mem)
    pycallback(py_mem)
    print "done"

def start_emulator(raw=None, size=0, pycb=None):
    global pycallback
    cdef long ptr = 0
    cdef void *c_raw = NULL
    cdef char *dummy = NULL
    pycallback = pycb
    cdef c_cb_ptr c_cb = NULL

    if pycb is not None:
        c_cb = &callback
        print "callback", hex(<long>c_cb)

    save = raw
    if save is not None:
        print "CTYPES:", ctypes.byref(save)
        ref = ctypes.byref(save)
        print "ref:", ref
        a = ctypes.addressof(save)
        print "addr:", hex(a)
        print dir(a)
        ptr = a
        c_raw = <void *>ptr
        dummy = <char *>c_raw
        # for i in xrange(1000):
        #     dummy[i] = 'm';
        start_shmem(c_raw, size, c_cb)
    else:
        start_shmem(NULL, 0, c_cb)
