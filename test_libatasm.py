#!/usr/bin/env python

from omnivore.assembler import find_assembler

assembler_cls = find_assembler("atasm")
assembler = assembler_cls()

asm = assembler.assemble("libatasm/atasm/tests/works.m65")

if asm:
    print(asm.segments)
    print(asm.equates)
    print(asm.labels)
else:
    print(asm.errors)
