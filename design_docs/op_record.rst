.. _op_record:

======================================================
Operation History & Operation Record Definitions
======================================================


Every frame is broken down into an operation history (op history). It consists
of 2 categories: operations and the changes produced by those operations. The
op history starts with a complete list of all the variables that will be
tracked by the debugger; at minimum: the registers, stack pointer, status
register and program counter. Other variables could be tracked as well, and to
minimize the size of the op history list, the list of variables of interest
could be specified at runtime as a subset of all the available variables.

An operation is a CPU instruction or event that changes the state of the
emulator. The type of events that are not CPU instructions would be things like
non-maskable interrupts or emulator events like the frame start or end markers.

An operation will have at least 2 records, the :ref:`Type 10 <type10>` record
that signifies the instruction size, and at least one more record defining the
type of operation. Most operations will have more than two records; a typical
CPU instruction will produce 5 to 10 records.

Because of the variable-length nature of the records, a separate lookup table
is maintained to map the operation number with the location in the record array
of the Type 10 record.


Operation Records
===================

The op history is allocated as a list of 32 bit unsigned integers,
where internally the entries are used as a 4 byte array. Each 4 bytes are
broken down into a single byte specifying the type and the remaining 3 bytes as
the payload. The meaning of the payload is dependent on the type.

  +------+-----+-----+-----+
  |  0   |  1  |  2  |  3  |
  +------+-----+-----+-----+
  | Type |    Payload      |
  +------+-----+-----+-----+

In C, this is defined as a 4 byte structure:

.. code-block::

   typedef struct {
      uint8_t type;
      uint8_t payload1;
      uint8_t payload2;
      uint8_t payload3;
   } op_record_t;

which can be cast to another 4 byte structure where the final 2 bytes are
combined into a 16 bit value:

.. code-block::

   typedef struct {
      uint8_t type;
      uint8_t arg;
      uint16_t addr;
   } op_record_16_t;

The types are:

.. csv-table:: Record Types
   :widths: 10,90

   Type (hex), Description
   01, one byte register value (e.g. A, X, Y, SP, SR)
   02, two byte register value (e.g. scan line number 0 - 262)
   03, one byte value written to address
   04, one byte value read from address
   05, computed indirect address used in opcode
   06, program counter (PC)
   07, branch status
   10, instruction PC, size, & additional opcode records
   28, frame start
   29, frame end
   2E, NMI start (e.g. DLI, VBI)
   2F, NMI end (e.g. DLI, VBI)
   30, referenced address
   80, user input: instruction number
   81, user input: one byte register value (e.g. A, X, Y, SP, SR, etc.)
   82, user input: two byte register value (e.g. scan line number 0 - 262)
   83, user input: one byte value at address
   86, user input: program counter (PC)
   88, user input: keypress
   89, user input: joystick
   8a, user input: paddle
   8b, user input: mouse
   E0, emulator configuration
   F0, machine state text pointer (text encoding of registers + opcode)
   F1, result text pointer (text encoding of what changed after this opcode)
   FF, disassembler type

The payload descriptions are:


01: One Byte Register Value
---------------------------------

Registers or internal emulator state that consists of one byte. For example,
the 6502 has 3 registers: A, X, and Y; a stack pointer; and a status register
that can fit in a single byte.

   +----+-------------+-------+--------+
   | 0  | 1           | 2     | 3      |
   +----+-------------+-------+--------+
   | 01 | Register ID | Value | unused |
   +----+-------------+-------+--------+

Registers are defined:

.. csv-table:: Register ID
   :widths: 10,90

   ID (hex), Register
   00, CC (color clock at start of instruction, ANTIC xpos in atari800)
   01, A
   02, X
   03, Y
   04, SP (stack pointer)
   05, SR (status register, aka flags)

02: Two Byte Register Value
---------------------------------

Registers or internal emulator state that consists of two bytes. Note that the
Program Counter is treated as a special case and has its own instruction
history type.

   +----+-------------+----+----+
   | 0  | 1           | 2  | 3  |
   +----+-------------+----+----+
   | 02 | Register ID | Lo | Hi |
   +----+-------------+----+----+

Registers are defined:

.. csv-table:: Register ID
   :widths: 10,90

   ID (hex), Register
   00, SL (scan line, ANTIC ypos in atari800)


03: One Byte Value Written to Address
------------------------------------------------

Records a change of a value in main memory

   +----+-------------+----+----+
   | 0  | 1           | 2  | 3  |
   +----+-------------+----+----+
   | 03 | New value   | Lo | Hi |
   +----+-------------+----+----+


04: One Byte Value Read From Address
------------------------------------------------

Records a value read from main memory

   +----+-------+----+----+
   | 0  | 1     | 2  | 3  |
   +----+-------+----+----+
   | 04 | Value | Lo | Hi |
   +----+-------+----+----+

.. _type05:

05: Computed Address Used as Target
---------------------------------------------------

A destination address in memory as the result of any opcode that uses any of
the following:

   * absolute address (e.g. LDA $3000)
   * absolute address plus indexing (e.g. LDA $2000,Y)
   * indirect address (e.g. JMP ($200))
   * indirect address plus indexing (e.g. LDA ($80),X)

must create an entry in the instruction list that holds that address that was
accessed:

   +----+--------+----+----+
   | 0  | 1      | 2  | 3  |
   +----+--------+----+----+
   | 05 | unused | Lo | Hi |
   +----+--------+----+----+


06: Program Counter (pc)
----------------------------------------------------------------------

Changing the program counter as the result of the opcode, other than proceeding
on to the next instruction, must create an entry with the new PC. Examples
would be JMP, JSR, Branch taken, NMI, etc.

   +----+--------+----+----+
   | 0  | 1      | 2  | 3  |
   +----+--------+----+----+
   | 06 | unused | Lo | Hi |
   +----+--------+----+----+

07: Branch Status
----------------------------------------------------------------------

Flag to indicate that a branch instruction occurred and if the branch was taken

   +----+--------+----+----+
   | 0  | 1      | 2  | 3  |
   +----+--------+----+----+
   | 07 | Taken? |  unused |
   +----+--------+----+----+

where Taken? is 01 if the branch was taken or 00 if not.

.. _type10:

10: Instruction PC, Size & Additional Opcode Records
----------------------------------------------------------------------

This entry type marks the start of a CPU instruction. This records the PC of
the instruction and the number of bytes making up the opcode.

   +----+------------------------+----+----+
   | 0  | 1                      | 2  | 3  |
   +----+------------------------+----+----+
   | 10 | opcode length in bytes | Lo | Hi |
   +----+------------------------+----+----+

This record also includes the opcode and operands in some additional 4-byte
records immediately following this entry. A pseudo-instruction will have an
opcode length of zero bytes, meaning that no additional records will be
included.

If the opcode length is greater than zero, the number of additional entries is
``(opcode length + 3 / 4)``, so one record if the opcode length is between 1
and 4 bytes, two records for opcode sizes between 5 and 8 bytes, etc. For
example, for a 5 byte opcode, the 2 extra records would be encoded as:

   +-----------+-----------+-----------+-----------+
   | 0         | 1         | 2         | 3         |
   +-----------+-----------+-----------+-----------+
   | Opcode    | Operand 1 | Operand 2 | Operand 2 |
   +-----------+-----------+-----------+-----------+
   | Operand 4 | unused    | unused    | unused    |
   +-----------+-----------+-----------+-----------+



28: Frame Start
---------------------------------

Flag for the frame start, simply occurs as the first entry into the list of
steps.

   +------+-----+----+----+
   |  0   |  1  | 2  | 3  |
   +------+-----+----+----+
   | 28   | XHi | Lo | Hi |
   +------+-----+----+----+

The frame number is a 24 bit unsigned integer where XHi will be zero until the
frame number becomes larger than 65535. Frame numbers start at 1, with zero
indicating the state of the machine immediately after power-on but before
executing any instructions.

29: Frame End
---------------------------------

Flag for the end of the frame, occurs as the last entry into the list of steps.

   +------+----+----+-----+
   |  0   | 1  | 2  |  3  |
   +------+----+----+-----+
   | 29   |    unused     |
   +------+----+----+-----+



2E: NMI Start (e.g. DLI, VBI)
----------------------------------------------------------------------

When an NMI occurs, this pseudo-instruction is generated to add an entry in the
UI.

   +----+----------+--------+--------+
   | 0  | 1        | 2      | 3      |
   +----+----------+--------+--------+
   | 2E | NMI type | unused | unused |
   +----+----------+--------+--------+

2F: NMI End
----------------------------------------------------------------------

At the end of an NMI, this psuedo-instruction is generated. Note that NMIs may
nest, so multiple NMI start records can appear before an NMI end record. There
must be a NMI end for every NMI start, but they may be separated by frame
boundaries.

   +----+----------+--------+--------+
   | 0  | 1        | 2      | 3      |
   +----+----------+--------+--------+
   | 2F | NMI type | unused | unused |
   +----+----------+--------+--------+

30: Referenced Address
----------------------------------------------------------------------

An opcode that references an address in memory by any of the following means:

   * absolute address (e.g. LDA $3000)
   * absolute address plus indexing (e.g. LDA $2000,Y)
   * indirect address (e.g. JMP ($200))
   * indirect address plus indexing (e.g. LDA ($80),X)

must create an entry in the instruction list that holds the address that is
specified by the opcode. Note this is different than a :ref:`Type 05 record
<type05>` because the Type 05 record indicates the *actual address used*, where
the Type 30 record stores the address encoded into the opcode.

The reference flag indicates the type of access: read, write, branch target.

   +----+----------------+----+----+
   | 0  | 1              | 2  | 3  |
   +----+----------------+----+----+
   | 30 | reference flag | Lo | Hi |
   +----+----------------+----+----+

E0: Emulator Configuration
----------------------------------------------------------------------

Type E0 record are only used in :ref:`frame 0 <frame0>` for specifying the
intial power-on state of the emulator. They are variable-length records
consisting of the main E0 record and some number of additional records
described by the lengths encoded in the record:

   +----+----------------------------------+----------------+----------------+
   | E0 | text description length in bytes | config size Lo | config size Hi |
   +----+----------------------------------+----------------+----------------+

The config data and text description length describe additional 4 byte records
immediately following this record, in that order. Both the config data and text
description will start on a record (4-byte) boundary. The lengths will be
specified in the actual bytes, and the number of records will be calculated as
in the :ref:`Type 10 <type10>` record: ``(length + 3) / 4``.

For config data of 5 bytes and a text description of 13 bytes, the set of
records would look like:

   +----+----+----+----+
   | E0 | 05 | 00 | 0d |
   +----+----+----+----+
   | 41 | 54 | 41 | 52 |
   +----+----+----+----+
   | 49 | 00 | 00 | 00 |
   +----+----+----+----+
   | T  | V  |    | T  |
   +----+----+----+----+
   | Y  | P  | E  | :  |
   +----+----+----+----+
   |    | N  | T  | S  |
   +----+----+----+----+
   | C  | 00 | 00 | 00 |
   +----+----+----+----+

Note that the config data is opaque to the op history processing, it
is purely data for the emulator. Its size can be up to 64K in length, while the
text description is limited to 255 bytes.


F0: Machine State Text Pointer
----------------------------------------------------------------------

Placeholder entry in the instruction list for the generated text representing
the machine state of the emulator, including the values of the registers, the
program counter, and the the disassembly.

The 24-bit pointer is an offset into a separately allocated block of bytes that
contains C-style strings of ASCII (not Unicode) text representing the human-
readable output. Being C-style strings, the length is arbitrary and terminated
by a zero byte.

   +------+-----+-----+-----+
   |  0   |  1  |  2  |  3  |
   +------+-----+-----+-----+
   | F0   | 24-bit pointer  |
   +------+-----+-----+-----+

F1: Result Text Pointer
----------------------------------------------------------------------

Placeholder entry in the instruction list for the generated text representing
the change in state of the emulator resulting from the instruction given by the
Type F0 record, including registers that changed, addresses that were read
from, or addresses that were modified with new values.

The pointer is as defined in Type F0 records.

   +------+-----+-----+-----+
   |  0   |  1  |  2  |  3  |
   +------+-----+-----+-----+
   | F1   | 24-bit pointer  |
   +------+-----+-----+-----+

FF: Disassembler Type & Extra Opcode Info
----------------------------------------------------------------------

This record changes the disassembler type to the specified value, and remains
in effect until the next Type FF record is encountered.

   +----+-------------------+-------------+--------+
   | 0  | 1                 | 2           | 3      |
   +----+-------------------+-------------+--------+
   | FF | Disassembler type | cycle count | flag   |
   +----+-------------------+-------------+--------+

User Input Entries
==============================

There are two ways to get user input to the emulator. The first is in a separate array, passed to the emulator frame method. The second is during debugging when the user changes a value of some parameter in the middle of a frame
When the user is debugging and changes a value in mid-frame, these records will appear in the input history

80: User Input: instruction number
-------------------------------------------------

Flag to indicate the instruction number for the following user input records

   +------+-----+-----+-----+
   |  0   |  1  |  2  |  3  |
   +------+-----+-----+-----+
   | 80   | 24-bit pointer  |
   +------+-----+-----+-----+


81: User Input: One Byte Register Value
----------------------------------------------------------------------

82: User Input: Two Byte Register Value
----------------------------------------------------------------------

83: User Input: One Byte Value At Address
----------------------------------------------------------------------

86: User Input: Program Counter
----------------------------------------------------------------------

87: User Input: Keyboard
-------------------------------------------------

Keyboard state

   +----+---------+---------+-----------+
   | 0  | 1       | 2       | 3         |
   +----+---------+---------+-----------+
   | 87 | Keychar | Keycode | Modifiers |
   +----+-------- +---------+-----------+

88: User Input: Digital Joystick
-------------------------------------------------

Value for 8-way digital joystick, direction is a bitfield where bits 0 - 3
represent directions up|down|left|right. On is pressed, off is released.

   +------+----------------+----------------+----------------+
   | 0    | 1              | 2              | 3              |
   +------+----------------+----------------+----------------+
   | 88   | Port number    | Direction      | Buttons        |
   +------+----------------+----------------+----------------+

89: User Input: Analog Paddle
-------------------------------------------------

Value for 8-bit analog paddle

   +------+----------------+----------------+----------------+
   | 0    | 1              | 2              | 3              |
   +------+----------------+----------------+----------------+
   | 89   | Port number    | Value          | Buttons        |
   +------+----------------+----------------+----------------+


Op Records Used as Disassembly
====================================

Op records are used for each entry in a static disassembly. No result records,
user input, or emulator state records are used, so the only records needed are:

The types are:

.. csv-table:: Record Types
   :widths: 10,90

   Type (hex), Description
   10, instruction PC, size, & additional opcode records
   30, referenced address
   FF, disassembler type

Each op record is 4 bytes, and the smallest number of records needed will be 3.
The type 10 and type ff records are required, and the type 30 record is
optional since not all opcodes will have a referenced address.

Because the type 10 record is variable size, each entry in the disassembly op
history list can be of arbitrary size (up to the limit of 256 bytes per
opcode). For a 3-byte opcode that references an address, the set of records
would look like:

   +----+----+----+----+
   | 10 | xx | xx | 03 |
   +----+----+----+----+
   | xx | xx | xx | 00 |
   +----+----+----+----+
   | ff | xx | xx | 00 |
   +----+----+----+----+
   | 30 | xx | xx | xx |
   +----+----+----+----+
