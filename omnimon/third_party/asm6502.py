#!/usr/bin/env python
# asm6502.py

# NOTE 11/21/15: Used by permission of David Beazley

"""
A simple but powerful 6502 assembler

Author : David Beazley (http://www.dabeaz.com)
Copyright (C) 2010

Parses assembly language of the following form:

var=value               ; Variable assignment

label:   OP ADDR        ; Labeled opcode and address
         OP ADDR        ; Opcode and address

Addressing modes are as follows:

         #value         ; immediate mode (8-bit value)
         %value         ; zero-page mode
         %value,X       ; zero-page X indexed
         %value,Y       ; zero-page Y indexed
         value          ; absolute
         value,X        ; absolute Y indexed
         value,Y        ; absolute Y indexed
         [value]        ; indirect
         [value,X]      ; indirect, X indexed
         [value,Y]      ; indirect, Y indexed

values and labels can be any Python expression, but the final value must
evaluate to an integer value.   Use a numeric label to set the memory
location of instructions to follow.
"""
from collections import Callable
import re

# Exception used for errors
class AssemblyError(Exception): pass

# Functions used in the creation of object code (used in the table below)
def VALUE_L(pc, value):
    return value & 0xff

def VALUE_H(pc, value):
    return (value & 0xff00) >> 8

def RELATIVE_ADDR(pc, value):
    offset = value - (pc + 2)
    return offset & 0xff

# Table of 6502 opcodes and supported addressing modes
opcodes_6502 = {
    'ADC' : {
        'immed' :      [0x69, VALUE_L],
        'zerop' :      [0x65, VALUE_L],
        'zerop_x' :    [0x75, VALUE_L],
        'abs' :        [0x6D, VALUE_L, VALUE_H],
        'abs_x' :      [0x7D, VALUE_L, VALUE_H],
        'abs_y' :      [0x79, VALUE_L, VALUE_H],
        'indirect_x' : [0x61, VALUE_L],
        'indirect_y' : [0x71, VALUE_L],
        },
    'AND' : {
        'immed' :      [0x29, VALUE_L],
        'zerop' :      [0x25, VALUE_L],
        'zerop_x' :    [0x35, VALUE_L],
        'abs' :        [0x2D, VALUE_L, VALUE_H],
        'abs_x' :      [0x3D, VALUE_L, VALUE_H],
        'abs_y' :      [0x39, VALUE_L, VALUE_H],
        'indirect_x' : [0x21, VALUE_L],
        'indirect_y' : [0x31, VALUE_L],
        },
    'ASL' : {
        'accum' :      [0x0a],
        'zerop' :      [0x06, VALUE_L],
        'zerop_x' :    [0x16, VALUE_L],
        'abs' :        [0x0e, VALUE_L, VALUE_H],
        'abs_x' :      [0x1e, VALUE_L, VALUE_H],
        },
    'BIT' : {
        'zerop' :      [0x24, VALUE_L],
        'abs'   :      [0x2c, VALUE_L, VALUE_H],
       },
    'BPL' : {
        'immed' :      [0x10, VALUE_L],
        'abs'   :      [0x10, RELATIVE_ADDR],
        },
    'BMI' : {
        'immed' :      [0x30, VALUE_L],
        'abs'   :      [0x30, RELATIVE_ADDR],
        },
    'BVC' : {
        'immed' :      [0x50, VALUE_L],
        'abs'   :      [0x50, RELATIVE_ADDR],
        },
    'BVS' : {
        'immed' :      [0x70, VALUE_L],
        'abs'   :      [0x70, RELATIVE_ADDR],
        },
    'BCC' : {
        'immed' :      [0x90, VALUE_L],
        'abs'   :      [0x90, RELATIVE_ADDR],
        },
    'BCS' : {
        'immed' :      [0xb0, VALUE_L],
        'abs'   :      [0xb0, RELATIVE_ADDR],
        },
    'BNE' : {
        'immed' :      [0xd0, VALUE_L],
        'abs'   :      [0xd0, RELATIVE_ADDR],
        },
    'BEQ' : {
        'immed' :      [0xf0, VALUE_L],
        'abs'   :      [0xf0, RELATIVE_ADDR],
        },
    'BRK' : {
        'accum' :      [0x00],
        'immed' :      [0x00, VALUE_L],
        },
    'CMP' : {
        'immed' :      [0xc9, VALUE_L],
        'zerop' :      [0xc5, VALUE_L],
        'zerop_x' :    [0xd5, VALUE_L],
        'abs' :        [0xcD, VALUE_L, VALUE_H],
        'abs_x' :      [0xdD, VALUE_L, VALUE_H],
        'abs_y' :      [0xd9, VALUE_L, VALUE_H],
        'indirect_x' : [0xc1, VALUE_L],
        'indirect_y' : [0xd1, VALUE_L],
        },
    'CPX' : {
        'immed' :      [0xe0, VALUE_L],
        'zerop' :      [0xe4, VALUE_L],
        'abs'   :      [0xec, VALUE_L, VALUE_H],
        },
    'CPY' : {
        'immed' :      [0xc0, VALUE_L],
        'zerop' :      [0xc4, VALUE_L],
        'abs'   :      [0xcc, VALUE_L, VALUE_H],
        },
    'DEC' : {
        'zerop' :      [0xc6, VALUE_L],
        'zerop_x' :    [0xd6, VALUE_L],
        'abs' :        [0xce, VALUE_L, VALUE_H],
        'abs_x' :      [0xde, VALUE_L, VALUE_H],
        },
    'EOR' : {
        'immed' :      [0x49, VALUE_L],
        'zerop' :      [0x45, VALUE_L],
        'zerop_x' :    [0x55, VALUE_L],
        'abs' :        [0x4D, VALUE_L, VALUE_H],
        'abs_x' :      [0x5D, VALUE_L, VALUE_H],
        'abs_y' :      [0x59, VALUE_L, VALUE_H],
        'indirect_x' : [0x41, VALUE_L],
        'indirect_y' : [0x51, VALUE_L],
        },
    'CLC' : {
        'accum' :      [0x18],
        },
    'SEC' : {
        'accum' :      [0x38],
        },
    'CLI' : {
        'accum' :      [0x58],
        },
    'SEI' : {
        'accum' :      [0x78],
        },
    'CLV' : {
        'accum' :      [0xb8],
        },
    'CLD' : {
        'accum' :      [0xd8],
        },
    'SED' : {
        'accum' :      [0xf8],
        },
    'INC' : {
        'zerop' :      [0xe6, VALUE_L],
        'zerop_x' :    [0xf6, VALUE_L],
        'abs' :        [0xee, VALUE_L, VALUE_H],
        'abs_x' :      [0xfe, VALUE_L, VALUE_H],
        },
    'JMP' : {
        'abs' :        [0x4c, VALUE_L, VALUE_H],
        'indirect' :   [0x6c, VALUE_L, VALUE_H]
        },
    'JSR' : {
        'abs' :        [0x20, VALUE_L, VALUE_H],
        },
    'LDA' : {
        'immed' :      [0xA9, VALUE_L],
        'zerop' :      [0xA5, VALUE_L],
        'zerop_x' :    [0xB5, VALUE_L],
        'abs' :        [0xAD, VALUE_L, VALUE_H],
        'abs_x' :      [0xBD, VALUE_L, VALUE_H],
        'abs_y' :      [0xB9, VALUE_L, VALUE_H],
        'indirect_x' : [0xA1, VALUE_L],
        'indirect_y' : [0xB1, VALUE_L],
        },
    'LDX' : {
        'immed' :      [0xa2, VALUE_L],
        'zerop' :      [0xa6, VALUE_L],
        'zerop_y' :    [0xb6, VALUE_L],
        'abs' :        [0xae, VALUE_L, VALUE_H],
        'abs_y' :      [0xbe, VALUE_L, VALUE_H],
        },
    'LDY' : { 
        'immed' :      [0xa0, VALUE_L],
        'zerop' :      [0xa4, VALUE_L],
        'zerop_x' :    [0xb4, VALUE_L],
        'abs' :        [0xac, VALUE_L, VALUE_H],
        'abs_x' :      [0xbc, VALUE_L, VALUE_H],
        },
    'LSR' : {
        'accum' :      [0x4a],
        'zerop' :      [0x46, VALUE_L],
        'zerop_x' :    [0x56, VALUE_L],
        'abs' :        [0x4e, VALUE_L, VALUE_H],
        'abs_x' :      [0x5e, VALUE_L, VALUE_H],
        },
    'NOP' : {
        'accum' :      [0xea],
        },
    'ORA' : {
        'immed' :      [0x09, VALUE_L],
        'zerop' :      [0x05, VALUE_L],
        'zerop_x' :    [0x15, VALUE_L],
        'abs' :        [0x0D, VALUE_L, VALUE_H],
        'abs_x' :      [0x1D, VALUE_L, VALUE_H],
        'abs_y' :      [0x19, VALUE_L, VALUE_H],
        'indirect_x' : [0x01, VALUE_L],
        'indirect_y' : [0x11, VALUE_L],
        },
    'TAX' : {
        'accum' :      [0xaa],
        },
    'TXA' : {
        'accum' :      [0x8a],
        },
    'DEX' : {
        'accum' :      [0xca],
        },
    'INX' : {
        'accum' :      [0xe8],
        },
    'TAY' : {
        'accum' :      [0xa8],
        },
    'TYA' : {
        'accum' :      [0x98],
        },
    'DEY' : {
        'accum' :      [0x88],
        },
    'INY' : {
        'accum' :      [0xc8],
        },
    'ROL' : {
        'accum' :      [0x2a],
        'zerop' :      [0x26, VALUE_L],
        'zerop_x' :    [0x36, VALUE_L],
        'abs' :        [0x2e, VALUE_L, VALUE_H],
        'abs_x' :      [0x3e, VALUE_L, VALUE_H],
        },
    'ROR' : {
        'accum' :      [0x6a],
        'zerop' :      [0x66, VALUE_L],
        'zerop_x' :    [0x76, VALUE_L],
        'abs' :        [0x6e, VALUE_L, VALUE_H],
        'abs_x' :      [0x7e, VALUE_L, VALUE_H],
        },
    'RTI' : {
        'accum' :      [0x40],
        },
    'RTS' : {
        'accum' :      [0x60],
        },
    'SBC' : {
        'immed' :      [0xe9, VALUE_L],
        'zerop' :      [0xe5, VALUE_L],
        'zerop_x' :    [0xf5, VALUE_L],
        'abs' :        [0xeD, VALUE_L, VALUE_H],
        'abs_x' :      [0xfD, VALUE_L, VALUE_H],
        'abs_y' :      [0xf9, VALUE_L, VALUE_H],
        'indirect_x' : [0xe1, VALUE_L],
        'indirect_y' : [0xf1, VALUE_L],
        },
    'STA' : {
        'zerop' :      [0x85, VALUE_L],
        'zerop_x' :    [0x95, VALUE_L],
        'abs' :        [0x8D, VALUE_L, VALUE_H],
        'abs_x' :      [0x9D, VALUE_L, VALUE_H],
        'abs_y' :      [0x99, VALUE_L, VALUE_H],
        'indirect_x' : [0x81, VALUE_L],
        'indirect_y' : [0x91, VALUE_L],
        },
    'TXS' : {
        'accum' :      [0x9a],
        },
    'TSX' : {
        'accum' :      [0xba],
        },
    'PHA' : {
        'accum' :      [0x48],
        },
    'PLA' : {
        'accum' :      [0x68],
        },
    'PHP' : {
        'accum' :      [0x08],
        },
    'PLP' : {
        'accum' :      [0x28],
        },
    'STX' : {
        'zerop' :      [0x86, VALUE_L],
        'zerop_y' :    [0x96, VALUE_L],
        'abs' :        [0x8e, VALUE_L, VALUE_H],
        },
    'STY' : {
        'zerop' :      [0x84, VALUE_L],
        'zerop_x' :    [0x94, VALUE_L],
        'abs' :        [0x8c, VALUE_L, VALUE_H],
        },
    }

# Parse address modes for various 6502 instructions
def parse_address_mode(mode):
    # Accumulator or implicit. Example: INC
    if not mode or mode == 'A':    return ("accum","0")  

    # Immediate value. Example : LDA #13  
    if mode.startswith("#"):       return ("immed", mode[1:]) 

    # Strip unneeded whitespace if not an immediate value
    mode = mode.replace(' ','')

    # Zero-page address with indexing. Example : LDA %25, X
    if mode.startswith("%"):
        if mode.endswith(",X"):    return ("zerop_x", mode[1:-2])
        elif mode.endswith(",Y"):  return ("zerop_y", mode[1:-2])
        else:                      return ("zerop", mode[1:])

    # Indirect addressing.Example : LDA [0xFF00, X]
    if mode.startswith("("):   
        if mode.endswith(",X)"):   return ("indirect_x", mode[1:-3])
        elif mode.endswith("),Y"): return ("indirect_y",mode[1:-3])
        elif mode.endswith(")"):   return ("indirect", mode[1:-1])

    # Absolute address, with indexing. Example : LDA 0xFF00, X
    if mode.endswith(",X"):        return ("abs_x",mode[:-2])
    elif mode.endswith(",Y"):      return ("abs_y",mode[:-2])
    else:                          return ("abs",mode)

# Parse an opcode line into intermediate object code. Returns a tuple
# (value, objcode) where value is a string to be evaluated in the 2nd pass
def parse_opcode(line):
    fields = line.split(None,1)
    opcode = fields[0]
    arg = fields[1] if len(fields) == 2 else ""
    mode,value = parse_address_mode(arg)
    opcodemodes = opcodes_6502.get(opcode)
    if not opcodemodes:
        raise AssemblyError("Unknown opcode '%s'" % opcode)
    objcode = opcodemodes.get(mode)
    if not objcode:
        raise AssemblyError("Invalid addressing mode '%s' for opcode %s" % (arg,opcode))
    if mode.startswith("abs"):
        zpmode = mode.replace("abs", "zerop")
        zp_objcode = opcodemodes.get(zpmode)
        if zp_objcode is not None:
            zp_objcode = list(zp_objcode)
    else:
        zp_objcode = None
    return (value, list(objcode), zp_objcode)

# Takes a sequence of lines and strip comments and blanks
def strip_lines(lines):
    for line in lines:
        comment_index = line.find(";")
        if comment_index >= 0:
            line = line[:comment_index]
        line = line.strip()
        yield line

assign_pat = re.compile(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*=)')

# Parse lines into intermediate object code
def parse_lines(lines,symbols):
    for lineno,line in enumerate(lines,1):
        if assign_pat.match(line):
            exec(line,symbols)
        else:
            label, colon, statement = line.rpartition(":")
            try:
                yield lineno, label, parse_opcode(statement) if statement else (None,None)
            except AssemblyError as e:
                print("{0:4d} : Error : {1}".format(lineno,e))

# Assemble a sequence of lines into binary
def assemble_6502(lines,pc=0):
    objcode = []
    symbols = {}
    symbols['HIGH'] = lambda x : (x & 0xff00) >> 8
    symbols['LOW'] = lambda x : x & 0xff

    # Pass 1 : Parse instructions and create intermediate code
    for lineno, label, (value, icode) in parse_lines(lines,symbols):
        # Try to evaluate numeric labels and set the PC
        if label:
            try:
                pc = int(eval(label,symbols))
            except (ValueError,NameError):
                symbols[label] = pc

        # Store the resulting objcode for later expansion
        if icode:
            objcode.append((lineno,pc,value,icode))
            pc += len(icode)

    # Pass 2 : Create final object code by evaluating expressions
    execode = []
    for lineno, pc, value, icode in objcode:
        # Evaluate the value string
        try:
            symbols['PC'] = pc
            realvalue = eval(value,symbols)
            if isinstance(realvalue,str):
                realvalue = ord(realvalue) & 0xff
            if not isinstance(realvalue, int):
                raise TypeError("Integer expected in {0}".format(value))
        except Exception as e:
            print("{0:4d} : Error : {1}".format(lineno,e))
            realvalue = 0
        ecode = [op(pc,realvalue) if isinstance(op,Callable) else op
                 for op in icode]
        execode.append((lineno,pc,ecode))
    return execode

def assemble_text(text, pc=0):
    try:
        value, icode, zpicode = parse_opcode(text)
    except AssemblyError as e:
        raise
    symbols = {}
    symbols['HIGH'] = lambda x : (x & 0xff00) >> 8
    symbols['LOW'] = lambda x : x & 0xff
    symbols['PC'] = pc
    v = value.replace("$", "0x")
    try:
        realvalue = eval(v,symbols)
    except Exception, e:
        raise AssemblyError("Invalid number: %s" % value)
    if isinstance(realvalue,str):
        realvalue = ord(realvalue) & 0xff
    if not isinstance(realvalue, int):
        raise TypeError("Integer expected in {0}".format(value))
    if realvalue < 0x100 and zpicode is not None:
        icode = zpicode
    ecode = [op(pc,realvalue) if isinstance(op,Callable) else op
             for op in icode]
    return ecode


if __name__ == '__main__':
    import sys

    text = """lda #4
    sta 0xe40a
    lda (0x4567,X)
    lda (0x4567),Y
    lda 0x4567,Y
    lda 0x45
    lda 0x4567
    bmi 0x0040
    lda 0x4567,X
    lda 0x45,X
    lda $45,X
    lda 45,X
    rts""".upper()
    lines = strip_lines(text.splitlines())
    for line in lines:
        ecode = assemble_text(line)
        print line, [hex(a) for a in ecode]
