#!/usr/bin/env python
from multiprocessing import Process, Array, RawArray
import ctypes

import memtest

def frame(mem):
    global exchange
    print("got frame", exchange, hex(ctypes.addressof(exchange)))
    for i in range(65000):
        if exchange[i] > 0:
            print("first:", i)
            break
    print("fake:", len(mem), type(mem))
    for i in range(len(mem)):
        if mem[i] > 0:
            print("first (fake):", i)
            break
    print("DEBUG: mem")
    debug_video(mem)
    print("DEBUG: exchange")
    debug_video(exchange)

def debug_video(mem):
    offset = 0
    for y in range(16):
        for x in range(64):
            c = mem[x + offset]
            print(c, end=' ')
        print()
        offset += 64;

exchange = RawArray(ctypes.c_ubyte, 100000)
print(type(exchange), exchange)
print(exchange[0])
exchange[10] = 255
print(dir(exchange))
#shared = exchange.get_obj()
shared = exchange
print(dir(shared))
print(len(shared))
#pointer = ctypes.byref(shared)
pointer = ctypes.addressof(shared)
print(hex(pointer))
memtest.start_emulator(shared, len(shared), frame)
