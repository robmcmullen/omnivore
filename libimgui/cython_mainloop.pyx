# distutils: language = c++

cdef extern from "mainloop.h":
    cpdef int mainloop()

def mainentry():
    mainloop()
