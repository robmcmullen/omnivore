#!/usr/bin/env python

from omni8bit.pyatasm import Assemble

asm = Assemble("libatasm/atasm/tests/works.m65")

if asm:
    print(asm.segments)
    print(asm.equates)
    print(asm.labels)
else:
    print(asm.errors)
