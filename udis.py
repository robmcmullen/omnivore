#! /usr/bin/env python3
#
# Universal Disassembler
# Copyright (c) 2013-2015 by Jeff Tranter <tranter@pobox.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import fileinput
import argparse
import signal

# Flags


pcr = 1
und = 2
z80bit = 4

# Functions


def isprint(c):
    "Return if character is printable ASCII"
    if c >= '@' and c <= '~':
        return True
    else:
        return False


# Avoids an error when output piped, e.g. to "less"
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


# Parse command line options
parser = argparse.ArgumentParser()
parser.add_argument("filename", help="Binary file to disassemble")
parser.add_argument("-c", "--cpu", help="Specify CPU type (defaults to 6502)", default="6502")
parser.add_argument("-n", "--nolist", help="Don't list  instruction bytes (make output suitable for assembler)", action="store_true")
parser.add_argument("-a", "--address", help="Specify decimal starting address (defaults to 0)", default=0, type=int)
parser.add_argument("-u", "--undocumented", help="Allow undocumented opcodes", action="store_true")
parser.add_argument("-i", "--invalid", help="Show invalid opcodes as ??? rather than constants", action="store_true")
args = parser.parse_args()

# Load CPU plugin based on command line option.
# Looks for plugin in same directory as this program.
dir = os.path.dirname(os.path.realpath(__file__))
plugin = dir + os.sep + args.cpu + ".py"
try:
    exec(open(plugin).read())
except FileNotFoundError:
    print(("error: CPU plugin file '{}' not found.".format(plugin)), file=sys.stderr)
    print("The following CPUs are supported: 6502 65c02 6800 6809 6811 8051 8080 z80")
    sys.exit(1)

# Get filename from command line arguments.
filename = args.filename

# Current instruction address. Silently force it to be in valid range.
address = args.address & 0xffff

# Any flags for current instruction.
flags = 0

# Contains a line of output.
line = ""

# Open input file.
# Display error and exit if filename does not exist.
try:
    f = open(filename, "rb")
except FileNotFoundError:
    print(("error: input file '{}' not found.".format(filename)), file=sys.stderr)
    sys.exit(1)

# Variables:
# address - current instruction address
# opcode - binary instruction opcode (may be multiple bytes)
# length - length of current instruction
# mnemonic - assembler mnemonic for current instruction
# format - operand format string
# line - line to output
# leadin - extended opcode (true/false)

s = "                          "

# Print initial origin address
if args.nolist is False:
    print("{0:04X}{1:s}.org   ${2:04X}".format(address, s[0:maxLength*3+3], address))
else:
    print(" .org   ${0:04X}".format(address))

while True:
    try:
        b = f.read(1)  # Get binary byte from file

        if len(b) == 0:  # handle EOF
            if args.nolist is False:
                print("{0:04X}{1:s}end".format(address, s[0:maxLength*3+3]))
            break

        # Get op code
        opcode = ord(b)

        # Handle if opcode is a leadin byte
        if opcode in leadInBytes:
            b = f.read(1)  # Get next byte of extended opcode
            if len(b) == 0:  # Unexpected EOF
                break
            opcode = (opcode << 8) + ord(b)
            leadin = True
        else:
            leadin = False

        # Given opcode, get data from opcode table and address mode table for CPU.
        if opcode in opcodeTable:
            length = opcodeTable[opcode][0]
            mnemonic = opcodeTable[opcode][1]
            mode = opcodeTable[opcode][2]
            if len(opcodeTable[opcode]) > 3:
                flags = opcodeTable[opcode][3]  # Get optional flags
            else:
                flags = 0
            if mode in addressModeTable:
                format = addressModeTable[mode]
            else:
                print(("error: mode '{}' not found in addressModeTable.".format(mode)), file=sys.stderr)
                sys.exit(1)
        else:
            length = 1  # Invalid opcode
            format = ""
            mnemonic = "???"
        
        if flags & 2 == und and not args.undocumented:
            # currently only handles one-byte undocumented opcodes
            format = ""
            mnemonic = "???"
            

# Disassembly format:
# XXXX  XX XX XX XX XX  nop    ($1234,X)
# With --nolist option:
# nop    ($1234,X)

        # Add current address to output line
        if args.nolist is False:
            if leadin is True:
                line += "{0:04X}  {1:02X} {2:02X}".format(address, opcode // 256, opcode % 256)
                length -= 1
            else:
                line += "{0:04X}  {1:02X}".format(address, opcode)

        op = {}  # Array to hold operands

        # Get any operands and store in an array
        for i in range(1, maxLength):
            if (i < length):
                b = f.read(1)
                if len(b) == 0:  # Unexpected EOF
                    break
                op[i] = ord(b)  # Get operand bytes
                if args.nolist is False:
                    line += " {0:02X}".format(op[i])
            else:
                if args.nolist is False and leadin is False and i != length-1:
                    line += "   "

        if len(b) == 0:  # Unexpected EOF
            break

        # Handle relative addresses. Indicated by the flag pcr being set.
        # Assumes the operand that needs to be PC relative is the last one.
        # Note: Code will need changes if more flags are added.
        if flags & pcr:
            if op[length-1] < 128:
                op[length-1] = address + op[length-1] + length
            else:
                op[length-1] = address - (256 - op[length-1]) + length
            if op[length-1] < 0:
                op[length-1] = 65536 + op[length-1]

        # Format the operand using format string and any operands.
        if length == 1:
            operand = format
        elif length == 2:
            operand = format.format(op[1])
        elif length == 3:
            if flags & z80bit:
                opcode = (opcode << 16) + op[2]
                # reread opcode table for real format string
                length, mnemonic, mode, flags = opcodeTable[opcode]
                format = addressModeTable[mode]
                operand = format.format(op[1])
            else:
                operand = format.format(op[1], op[2])
        elif length == 4:
            operand = format.format(op[1], op[2], op[3])
        elif length == 5:
            operand = format.format(op[1], op[2], op[3], op[4])
        elif length == 6:
            operand = format.format(op[1], op[2], op[3], op[4], op[5])
        elif length == 7:
            operand = format.format(op[1], op[2], op[3], op[4], op[5], op[6])

        # Special check for invalid op code. Display as ??? or .byte depending on command line option.
        if mnemonic == "???" and not args.invalid:
            # Handle case where invalid opcode has a leadin byte.
            if leadin is True:
                if args.nolist is False:
                    mnemonic = "{0:s}.byte  ${1:02X},${2:02X}".format(s[0:(maxLength-length-2)*3], opcode // 256, opcode % 256)
                else:
                    mnemonic = ".byte  ${0:02X},${1:02X}".format(opcode // 256, opcode % 256)
            else:
                if isprint(chr(opcode)):
                    mnemonic = ".byte  '{0:c}'".format(opcode)
                else:
                    mnemonic = ".byte  ${0:02X}".format(opcode)

        # Need one more space if not in no list mode.
        if args.nolist is False:
            line += " "

        # Add mnemonic and any operands to the output line.
        if operand == "":
            line += " {0:s}".format(mnemonic)
        else:
            line += " {0:5s}  {1:s}".format(mnemonic, operand)

        # Print line of output
        print(line)

        # Update address, handlng wraparound at 64K.
        address = (address + length) & 0xffff

        # Reset variables for next line of output.
        line = ""
        operand = ""
        flags = 0

    except KeyboardInterrupt:
        print("Interrupted by Control-C", file=sys.stderr)
        break
