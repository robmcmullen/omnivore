# distutils: language = c++

cdef extern from "mainloop.h":
    cpdef int mainloop()

def mainentry():
    mainloop()

cdef public int call_to_python():
    print("in python")
