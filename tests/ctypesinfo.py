from ctypes import *

class Info(Structure):
   _fields_ = [("input",c_int),
              ("out",c_int)]

info = Info()

info.input = c_int(32)
info.out = c_int(121)

lib = CDLL("./sharedLib.so").getVal
a = lib(byref(info))

print "python"
print info.input
print info.out
