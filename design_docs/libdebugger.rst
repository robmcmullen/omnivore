==============================
Libdebugger Code Design
==============================


Overview
==========

Libdebugger is a frame-based debugger that implements breakpoints based on
history generated within each frame. This frees emulators from having to
process breakpoints within the emulation code:

 * simplifying and speeding up emulator code by removing debugger 
 * multiple emulators can have the same debugging interface

Emulator requirements:

 * frame-based (corresponding to a NTSC or PAL TV frame, for example) or an
   arbitrary frame size may be chosen
 * generating a single frame is a relatively cheap operation, on the order of
   hundreds of frames per second if run as fast as possible
 * able to save/restore entire emulator state, but only at frame boundaries
 * deterministic; that is: restoring a frame and running it again must create
   the same frame data as before

Emulator modifications needed:

 * record changes in emulator state after each instruction, saved in a list of
   deltas
 * change emulator state in mid-frame for user debugging

The debugger will only be able to break on data saved in the deltas, anything
not recorded in deltas won't be available.


Debugging Process
======================

Since the emulator doesn't handle breakpoints itself, it relies on the front-
end to handle any breakpoints. The emulator will generate the emulation for an
entire frame to produce the instruction history for that frame, and return this
data to the front-end.

If no breakpoints are defined, the front-end displays the results of the frame
(i.e. displaying the emulated screen, playing any sound generated during this
frame, etc.) and continues to process the next frame. Because the emulator
itself is not checking breakpoints at every instruction, the emulator code will
likely be faster than a typical emulator since it does not have to loop through
all breakpoints at each instruction.

If any breakpoints are defined, the front-end then steps through the
instruction history seeing if any breakpoint conditions are met. Because the
frame has already been generated, the front-end is not actually stepping
through the code as it happens, but is stepping through the history of the code
in that frame, *presented as if it were currently happening*.

The user stepping through the code represents time, and it is broken down into
the instructions processed in the past, the instruction about to be processed,
and future instructions. As the user steps through the code, the instructions
are displayed from some point in the past up to the current instruction, and
the future instructions are not displayed. As the stepping continues,
instructions from the list of future instructions become visible and the UI is
updated with the changes to the emulator state.

Again, the frame has already been run, and the front end is only stepping
through the instruction history as if the emulator was performing the actions
of the current instruction in the history. The instruction history contains all
the changes to the emulator state that the user is interested in debugging,
so the results at any instruction should appear no different to the user than
if it were implemented as a typical debugging emulator where it is returning
control to the front-end after each instruction.

The front-end will not be able to see the entire internal state of the emulator
at every instruction, because that would require a full emulator save state at
every instruction, obviously being too memory intensive. Instead, this design
saves the full emulator state at frame boundaries only, and only the change to
the emulator state is recorded at each instruction.

This is a much smaller set of data, and allows the entire emulator state to be
reconstructed at any instruction by starting from the full emulator state at
the beginning of the frame and successively applying the changes at each
instruction to find the state at any subsequent point in the frame.


Emulator State Subset
---------------------------------------

Recording *every* change to the emulator state at each instruction would be
unwieldy and likely slow the emulator unnecessarily. Instead, the user will
define the set of emulator state variables to be saved at each instruction.
This will have the effect of limiting which data can be tested when defining
breakpoints.

Registers and CPU state are always saved, but for instance in the **atari800**
emulator there are many custom chips, each with their own internal state. It
would not be efficient to save all the POKEY register changes if the user were
not interested in debugging POKEY issues.

Each emulator will provide a list of possible emulator state variables, and it
will be up to the user to choose which of the variables to save at each
instruction. The more variables saved, the higher the memory requirements and
slower the emulation.


Backwards in Time
--------------------------------------

The ability to step backwards in time is gained, essentially, as a side effect
of this debugging system. Because the emulator state presented in the UI is
built from the instruction history, the emulator state at any point in history
can be reconstructed by starting from the state at the start of a frame and
applying changes until the desired instruction is reached.

Moving forward in time by one instruction uses the delta contained in the next
set of records to modify the emulator state to reflect the next instruction. If
reverse deltas were stored, moving one instruction backward in time would
simply apply this reverse delta and result in the emulator state for the
previous instruction.

Since reverse deltas are not used, moving backward involves using the emulator
state from the frame start and applying changes up to the previous instruction.
This is obviously not as fast as moving forward in time, but moving backward in
time is likely to be controlled by the user, one step at a time, so any delay
in moving would probably be unnoticeable with the normal UI refresh rate.


Modifications to Emulator During Debugging
----------------------------------------------------

The emulator is only capable of generating complete frames, so debugging would
be limited to observation of the instructions generated within the frame. If
changes to the emulator state were only allowed at frame boundaries, then only
observation of the emulator instruction history would be possible.

In order to make changes to the emulator state in the middle of a frame, the
emulator needs to be modified to accept a user change at a certain instruction
count. But, since the user can't actually break the emulator in the middle of
the frame, the change and the instruction count at which the change happens
must be supplied to the emulator at the start of a new frame.

Because more than one change may be requested by the user, a list of changes
and instruction counts at which each change is applied must be generated by the
front-end. This list is supplied to the emulator when the frame is re-run. The
emulator will regenerate the frame, and up until the first change will produce
an identical instruction history. Once the instruction count matches the count
in the change list and before it executes the next instruction, the emulator
will update its state as specified, then resume executing instructions.

The instruction history will diverge from the original history, starting at the
first instruction history count containing an emulation state change. The
front-end will present the results to the user, and because a single emulation
frame is a cheap operation, it should appear to the user as if this debugger
were operating as a traditional debugger.


Frame History
=========================

The frame history at any point is a list of emulator frames starting from the
power-on state of the emulator to the current frame. Every frame must contain a
pointer to its parent, so the complete history back to the start of the
emulator can be traversed.

The front-end may allow branches, so in this case the frame history would be
defined as a tree structure, meaning any frame might have multiple children.
This would correspond to multiple execution paths; for example, this may happen
when a changes is made to a frame and the emulator is run again from that
frame. The original frame history can be retained, and the new history branches
off from the parent frame (the frame before the change was made).



Instruction History
==================================

Every frame is broken down into the instruction history. It consists of 2
categories: operations and the changes produced by those operations. The
instruction history starts with a complete list of all the variables that will
be tracked by the debugger; at minimum: the registers, stack pointer, status
register and program counter. Other variables could be tracked as well, and to
minimize the size of the instruction history list, the list of variables of
interest could be specified at runtime as a subset of all the available
variables.


Encoding the Instruction History
===============================================

The instruction history is allocated as a list of 32 bit unsigned integers,
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
   } instruction_delta_t;

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

05: Computed Address Used In Opcode
---------------------------------------------------

An opcode that references an address in memory by any of the following means:

   * absolute address (e.g. LDA $3000)
   * absolute address plus indexing (e.g. LDA $2000,Y)
   * indirect address (e.g. JMP ($200))
   * indirect address plus indexing (e.g. LDA ($80),X)

must create an entry in the instruction list that holds that address that was
accessed:

   +----+----+----+--------+
   | 0  | 1  | 2  | 3      |
   +----+----+----+--------+
   | 05 | Lo | Hi | unused |
   +----+----+----+--------+


06: Program Counter (pc)
----------------------------------------------------------------------

Changing the program counter as the result of the opcode, other than proceeding
on to the next instruction, must create an entry with the new PC. Examples
would be JMP, JSR, Branch taken, NMI, etc.

   +----+----+----+--------+
   | 0  | 1  | 2  | 3      |
   +----+----+----+--------+
   | 06 | Lo | Hi | unused |
   +----+----+----+--------+

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

   +----+----+----+------------------------+
   | 0  | 1  | 2  | 3                      |
   +----+----+----+------------------------+
   | 10 | Lo | Hi | opcode length in bytes |
   +----+----+----+------------------------+

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

Flag for instruction history start, simply occurs as the first entry into the
instruction history list.

   +------+----+----+-----+
   |  0   | 1  | 2  |  3  |
   +------+----+----+-----+
   | 28   | Lo | Hi | XHi |
   +------+----+----+-----+

The frame number is a 24 bit unsigned integer where XHi will be zero until the
frame number becomes larger than 65535. Frame numbers start at 1, with zero
indicating the state of the machine immediately after power-on but before
executing any instructions.

29: Frame End
---------------------------------

Flag for instruction history end, occurs as the last entry into the instruction
history list.

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

   +----+----+----+--------+
   | 0  | 1  | 2  | 3      |
   +----+----+----+--------+
   | 30 | Lo | Hi | unused |
   +----+----+----+--------+

E0: Emulator Configuration
----------------------------------------------------------------------

Type E0 record are only used in :ref:`frame 0 <frame0>` for specifying the
intial power-on state of the emulator. They are variable-length records
consisting of the main E0 record and some number of additional records
described by the lengths encoded in the record:

   +----+----------------+----------------+----------------------------------+
   | E0 | config size Lo | config size Hi | text description length in bytes |
   +----+----------------+----------------+----------------------------------+

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

Note that the config data is opaque to the instruction history processing, it
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

FF: Disassembler Type
----------------------------------------------------------------------

This record changes the disassembler type to the specified value, and remains
in effect until the next Type FF record is encountered.

   +----+-------------------+--------+--------+
   | 0  | 1                 | 2      | 3      |
   +----+-------------------+--------+--------+
   | FF | Disassembler type | unused | unused |
   +----+-------------------+--------+--------+

User Input Entries
==============================

There are two ways to get user input to the emulator. The first is in a separate array, passed to the emulator frame method. The second is during debugging when the user changes a value of some parameter in the middle of a frame
When the user is debugging and changes a value in mid-frame, these records will appear in the input history

80: User Input: instruction number
-------------------------------------------------

Flag to indicate the instruction number for the following user input records

   +------+----+----+-----+
   |  0   | 1  | 2  |  3  |
   +------+----+----+-----+
   | 28   | Lo | Hi | XHi |
   +------+----+----+-----+


81: User Input: One Byte Register Value
----------------------------------------------------------------------

82: User Input: Two Byte Register Value
----------------------------------------------------------------------

83: User Input: One Byte Value At Address
----------------------------------------------------------------------

86: User Input: Program Counter
----------------------------------------------------------------------





Displaying the Current Emulator State
=============================================

Presenting the user with the instruction history involves stepping through all
the deltas from the frame start until the desired instruction is reached.

For the first implementation of this system, no caching is performed. It is
postulated that the successive applying of the deltas will be fast enough so as
to be lost in the noise of the speed of the user advancing the UI. This will be
reevaluated once the implementation is written.

The debugger UI is expected to display information containing the processor
state, the current instruction, any labels, and other useful information. For
example:

.. code-block::

   260 102 | ff ad cc ---IZC ff c2ee  a9 00     lda #$00        A=00 
   260 104 | 00 ad cc ---IZC ff c2f0  91 04     sta (RAMLO),y   $adcc=00 (was ff) 
   260 110 | 00 ad cc ---IZC ff c2f2  d1 04     cmp (RAMLO),y   $adcc=00 
   261  10 | 00 ad cc ---IZC ff c2f4  f0 02     beq $c2f8       (taken) 
   261  13 | 00 ad cc ---IZC ff c2f8  c8        iny             Y=cd N=1 Z=0 
   261  15 | 00 ad cd N--I-C ff c2f9  d0 e9     bne $c2e4       (taken) 

Other displays in the user interface could display the complete memory of the
emulator, visualizations of memory accesses based on the instruction history,
or internal status of any memory-mapped hardware or coprocessors (like the GTIA
or ANTIC in the atari800 emulator). This is not an exhaustive list; many other
features are possible using the instruction history data.

To see the machine state at any point in the instruction history, a data
structure is needed to hold the successive application of the deltas contained
in the instruction history. An example of this structure is defined as follows:

.. code-block::

   typedef struct {
      uint32_t frame_number;

        /* instruction */
      uint16_t pc; /* special two-byte register for the PC */
      uint16_t opcode_ref_addr; /* address referenced in opcode */
      uint8_t instruction_length; /* number of bytes in current instruction */
      uint8_t instruction[255]; /* current instruction */

        /* result of instruction */
      uint8_t reg1[256]; /* single byte registers */
      uint16_t reg2[256]; /* two-byte registers */
      uint16_t computed_addr; /* computed address after indirection, indexing, etc. */
      uint8_t ram[256*256]; /* complete 64K of RAM */
   } current_state_t;

Because the instruction history will have variable numbers of records for each
instruction, a lookup table is generated as a post-processing step by
libdebugger, after the emulator generates a frame. It is a simple list, indexed
by line number to be displayed in the UI, pointing to the index in the
instruction history list of the :ref:`Type 01 record <type01>` for the
instruction.

.. code-block::

   uint16_t ui_line_lookup[...]; /* allocated */



Sample Instruction History
-----------------------------------

This example imagines a 6502 machine with 16 bytes of RAM at addresses 0 - f.
An instruction history might look like this:


.. csv-table:: Instruction History
   :widths: 10,10,10,10,10,40

   Entry, Record Type, B1, B2, B3, Description
   0, 10,00,80,00,PC = $8000, 0 bytes in the instruction: UI line #0
   1, 21,01,00,00,Frame #1 start
   2, 10,00,80,03,PC = $8000, 3 bytes in the instruction: UI line #1
   3, 20,00,60,00,INSTRUCTION: JSR $6000
   4, 03,02,ff,01,store low byte of return addr on stack
   5, 03,80,fe,01,store high byte of return addr on stack
   6, 01,04,fd,00,move stack pointer down by 2
   7, 06,00,60,00,PC changed to $6000
   8, 10,00,60,02,PC = $6000, 2 bytes in the instruction: UI line #2
   9, a9,00,00,00,INSTRUCTION: LDA #$00
   10, 01,01,00,00,register A = 0
   11, 01,05,02,00,status register = $02 (Z = 1)
   12, 10,02,60,02,PC = $6002, 2 bytes in the instruction: UI line #3
   13, 85,08,00,00,INSTRUCTION: STA $08
   14, 03,00,08,00,$0 stored in address $0008
   15, 10,04,60,01,PC = $6004, 1 bytes in the instruction: UI line #4
   16, 85,09,00,00,INSTRUCTION: STA $09
   17, 03,00,09,00,$0 stored in address $0009
   18, 10,04,60,01,PC = $6006, 1 bytes in the instruction: UI line #5
   19, 60,00,60,00,INSTRUCTION: RTS
   20, 01,04,ff,00,move stack pointer up by 2
   21, 06,03,80,00,PC Changed to $8004
   22, 10,00,80,02,PC = $8003, 2 bytes in the instruction: UI line #6
   23, a2,08,00,00,INSTRUCTION: LDX #$08
   24, 01,02,08,00,register X = 8
   25, 01,05,00,00,status register = $00 (Z = 0)
   26, 10,00,80,02,PC = $8005, 2 bytes in the instruction: UI line #7
   27, a2,08,00,00,INSTRUCTION: LDA $00,X
   28, 30,00,00,00,opcode references address $0000
   29, 05,08,00,00,computed address = $8 ($00 + X, X=8)
   30, 04,08,00,00,read value 0 from $08
   31, 01,02,08,00,register A = 8
   32, 01,05,02,00,status register = $02 (Z=1)
   33, 10,00,80,02,PC = $8007, 2 bytes in the instruction: UI line #8
   34, 95,08,00,00,INSTRUCTION: STA ($08),X
   35, 30,02,00,00,opcode references address $0008
   36, 05,08,00,00,computed address = $8 ($08=0, $09=0, ($08)=0, 0 + X, X=8)
   37, 03,08,00,00,write value 8 to $08
   38, 10,09,80,00,PC = $8009, 0 bytes in the instruction: UI line #9
   39, 2e,02,00,00,NMI start: DLI
   40, 03,09,ff,01,store low byte of return addr on stack
   41, 03,80,fe,01,store high byte of return addr on stack
   42, 03,02,fd,01,store status register on stack
   43, 01,04,fc,00,move stack pointer down by 3
   44, 01,05,06,00,status register = $06 (I=1, Z=1)
   45, 06,00,c0,00,PC changed to $c000
   46, 10,00,c0,03,PC = $c000, 3 bytes in instruction: UI line #10
   47, 2c,0f,d4,00,INSTRUCTION: BIT $d40f (NMIRES)
   48, 30,0f,d4,00,opcode references $d40f
   49, 01,04,84,00,status register = $80 (DLI bit set: N=1, I=1, Z=0)
   50, 10,03,c0,02,PC = $c003, 2 bytes in instruction: UI line #11
   51, 30,1a,00,00,INSTRUCTION: BMI $c01f
   52, 30,1f,c0,00,opcode references $c01f
   53, 07,01,00,00,branch taken
   54, 06,1f,c0,00,PC Changed to $c01f
   55, 10,1f,c0,02,PC = $c01f, 1 bytes in instruction: UI line #12
   56, 40,00,00,00,INSTRUCTION: RTI
   57, 01,05,02,00,status register = $02
   58, 06,09,80,00,PC Changed to $8009
   59, 10,09,80,00,PC = $8009, 0 bytes in the instruction: UI line #13
   60, 2f,02,00,00,NMI end: DLI
   61, 10,09,80,01,PC = $8009, 1 bytes in the instruction: UI line #13
   62, 38,00,00,00,INSTRUCTION: SEC
   63, 01,05,03,00,status register = $03 (Z=1, C=1)
   64, 10,09,80,00,PC = $800a, 0 bytes in the instruction: UI line #14
   65, 29,00,00,00,Frame end

For this simple 6502 emulator with 16 bytes ram, the ``current_state_t`` structure could be cast to this:

.. code-block::

   typedef struct {
      uint32_t frame_number;

        /* instruction */
      uint16_t pc;
      uint16_t opcode_ref_addr;
      uint8_t instruction_length; /* number of bytes in current instruction */
      uint8_t instruction[255]; /* current instruction */

        /* result of instruction */
      uint8_t color_clock;
      uint8_t a;
      uint8_t x;
      uint8_t y;
      uint8_t sp;
      uint8_t sr;
      uint8_t reg1[250]; /* filler */
      uint16_t scan_line;
      uint16_t reg2[255];
      uint8_t ram[16];
      uint8_t unassigned_ram[65520] /* remainder of 64K of RAM */
   } current_state_t;

This structure is filled at the beginning of the frame and modified by the
instruction history deltas as instructions are processed for display in the UI. At the beginning of the frame, the emulator state is copied directly into the structure. At power-on, this data might be:

.. code-block::

   current_state_t c;
   c.frame_number = 0;
   c.pc = 0;
   c.instruction_length = 0;
   c.a = 0;
   c.x = 0;
   c.y = 0;
   c.sp = 0xff;
   c.sr = 0;
   c.color_clock = 0;
   c.scan_line = 0;
   memcpy(c.ram, emulator_ram, 16);

As instructions are processed by the UI for display, the deltas are used to
modify this structure. Using the example above, the UI uses the
``ui_line_lookup`` array to determine which history entry starts the definition
for the text display. For the example above, it contains these values:

   0, 2, 8, 11, 15, 18, 26, 33, 38, 46, 50, 55, 59, 61, 64

which maps the line number that will hold the text representation of this
instruction to the position in the instruction history array of the Type 10
record (or Type 0 record in the case of the very first entry).

Index 0 of this array points to the frame start entry:

.. csv-table:: Instruction History, index 0 - 1
   :widths: 10,10,10,10,10,40

   0, 10,00,80,00,PC = $8000, 0 bytes in the instruction: UI line #0
   1, 21,01,00,00,Frame #1 start

so when UI line #0 gets requested by the UI, the ``current_state_t`` array is modified by the Type 10 and Type 21 records to become:

.. code-block::

   c.frame_number = 1;

   /* instruction */
   c.pc = 0x8000;
   c.instruction_length = 0;

   /* results */
   c.a = 0;
   c.x = 0;
   c.y = 0;
   c.sp = 0xff;
   c.sr = 0;
   c.color_clock = 0;
   c.scan_line = 0;

which may be cached or recomputed when needed again. Were it to be cached, it
would be associated with UI line #0. Note that this means the
``current_state_t`` data associated with an output text line is the instruction
on that line with the state of the machine *after* that instruction is
executed.

This state also becomes the input for the next instruction. Index 1 of the
``ui_line_lookup`` array points to this sequence of deltas:

.. csv-table:: Instruction History, index 2 - 7
   :widths: 10,10,10,10,10,40

   2, 10,00,80,03,PC = $8000, 3 bytes in the instruction: UI line #1
   3, 20,00,60,00,INSTRUCTION: JSR $6000
   4, 03,02,ff,01,store low byte of return addr on stack
   5, 03,80,fe,01,store high byte of return addr on stack
   6, 01,04,fd,00,move stack pointer down by 2
   7, 06,00,60,00,PC changed to $6000

the ``current_state_t`` structure is modified by all the history entries through entry index 7 to become the results of executing that instruction:

.. code-block::

   c.frame_number = 1;

   /* instruction */
   c.pc = 0x8000;
   c.instruction_length = 3;
   c.instruction[0] = 0x20
   c.instruction[1] = 0x00
   c.instruction[2] = 0x60

   /* results */
   c.a = 0;
   c.x = 0;
   c.y = 0;
   c.sp = 0xfd;
   c.sr = 0;
   c.color_clock = 0;
   c.scan_line = 0;
   c.ram[0x1ff] = 0x02;
   c.ram[0x1fe] = 0x80;

and is cached (if caching is implemented) as the emulator state for UI line #1.


Creating Instruction History in Emulator
===============================================

The libdebugger code includes some convenience functions to create instruction history. At the start of an emulation frame, a call to:

.. code-block::

   instruction_history_t *get_working_instruction_history(int max_delta, int max_ui_lines);

will return data storage space for the instruction history that will be built
as the emulation processes opcodes during the frame. The
``instruction_history_t`` structure is defined as:

.. code-block::

   typedef struct {
      uint32_t frame_number;
      uint32_t num_allocated_delta;
      uint32_t num_delta; /* current count of deltas */
      uint32_t num_allocated_ui_line_lookup;
      uint32_t num_ui_line_lookup; /* current count of ui lines */
      uint32_t unused[3]; /* reserved, maintaining 64 bit alignment */
      instruction_delta_t *delta; /* allocated */
      instruction_delta_t *current_delta;
      uint32_t *ui_line_lookup; /* allocated */
      uint32_t *current_ui_line;
   } instruction_history_t;

The parameters ``max_delta`` and ``max_ui_lines`` is not precisely known at the
start of any emulation frame because opcodes take different number of clock
cycles. So, it is advisable to overestimate the number during this call. The
code actually reuses the same data for every emulation frame, and the call
to:

.. code-block::

   instruction_history_t *finalize_instruction_history();

will create a copy of the working instruction history that is sized to exactly
hold the data. It will look at the array sizes determined by ``num_delta`` and
``num_ui_line_lookup`` and create allocated sizes for ``delta`` and
``ui_line_lookup`` that exactly match those numbers.

Internally, the code allocates one block of memory for the size of the
``instruction_history_t`` structure *plus* the sizes of the deltas and ui line
lookup table, and partitions that into 3 areas with the delta and ui line lookup pointers using addresses within this allocation.

For example, in a 64 bit system, ``sizeof(instruction_history_t)`` is 64 bytes,
and if there are 10,000 entries in the ``delta`` array and 2000 in the
``ui_line_lookup`` array, the allocation would be ``64 + 10000*4 + 2000*4`` or
48064 bytes in a single array:

   +----+---------------------------------------+-------------+
   | 64 |                 40000                 |    8000     |
   +----+---------------------------------------+-------------+

The ``delta`` pointer would then point to 64 bytes beyond the start of the
array, and the ``ui_line_lookup`` points to 40064 bytes after the start of the
array.

The call to ``finalize_instruction_history`` uses the counts of the entries in
both allocated arrays to allocate a new block of memory with no wasted space.
Using the example above, if ``num_delta = 4055`` and ``num_ui_line_lookup =
822``,  the exactly-fitted allocation would be ``64 + 4055*4 + 822*4`` or 19572
bytes:

   +----+-------------------+------+
   | 64 |       16220       | 3288 |
   +----+-------------------+------+


Emulation Frame Storage
=================================

An emulation frame consists of the save state of the machine, the video and
audio output resulting from that frame, and the exactly-fitted
``instruction_history_t`` array as described above.

All this data is from the *end* of the frame, meaning it is the state of the
machine when the frame is complete. To re-run the frame, the machine state from
the *previous* frame must be loaded, then the instructions making up this frame
executed. In other words, the instructions making up the
``instruction_history_t`` array transform the machine state from the previous
frame's end state to the current frame's end state.

.. _frame0:

Frame 0: Emulator Configuration Frame
---------------------------------------------------

The emulation frame starting from power-on is a special case, since there is no
previous frame in this case. Frame number 0 is marked as the power-off state,
so the end of frame 0 is the power-on state. This means frame number 1 is the
first frame that contains CPU instructions and a real machine state. Restoring
frame 1 is essentially cold-starting the computer as the machine state will be
reset to the same power-on conditions as defined in frame 0.

Frame 0 can be thought of as the emulator configuration frame, so any data
needed to set up the emulator can be stored in this frame's instruction
history. This configuration data can be TV type (PAL vs NTSC), RAM size,
Operating System Version, ROM cartridges present, and even machine type (in the
case of an emulator that supports multiple machines like the atari800 emulator
supporting both the Atari 8-bit computers and the Atari 5200 game system).


Emulator Operation
================================

With libdebugger, the emulator only processes full frames and leaves all post-
processing (including debugging!) to the front-end UI.

The interface into the emulator is therefore small. All that is required is:

 * emulator cold-start boot configuration
 * emulator export machine state to buffer
 * emulator import machine state from buffer
 * emulator process frame

The example function below are from a sample implementation emulator called
**lib6502**, a simple 6502 emulator with optional support for some Apple ][+
features.

Cold-Start Boot Configuration
----------------------------------

The cold start configuration function takes a list of parameters to set up the
emulator before any instructions are executed. The ``lib6502_clear_config``
function should be called before any calls to ``lib6502_add_config_data``. Note
that ``lib6502_add_config_data`` may be called an arbitrary number of times
before any frames are generated, but when the emulator is processing frame 1
and beyond, calls are ignored and an error is returned.

If the emulator is restored to frame 0 or a call to ``lib6502_reset_emulator``
is made, calls can be made to reconfigure the emulator. A call to
``lib6502_clear_config`` is implicit in the call to ``lib6502_reset_emulator``.

.. code-block::

   int lib6502_reset_emulator();
   int lib6502_clear_config();
   int lib6502_add_config_data(uint8_t *config_data, uint8_t *description);

Export Save State
--------------------------

This function fills a buffer with the save state of the machine, such that a
call to the restore function below will return the emulator to the same
internal state as when it was saved.

.. code-block::

   int lib6502_export_state(lib6502_state_t *buf);

Import Save State
--------------------------

This function restores the emulator internal state using the previously
imported buffer exported through the function above.

.. code-block::

   int lib6502_import_state(lib6502_state_t *buf);

Process Frame
-------------------------------------

This is the only emulation function available: process a complete emulation
frame. It starts from the current internal state of the emulator and executes
instructions to complete one TV frame of emulation.

.. note::

   The final instruction of a frame may cross the frame boundary if cycle count
   is higher than the number of cycles remaining in the frame. If this happens,
   the subsequent frame will not begin at cycle zero of the frame, but will
   skip the number of extra cycles in from the previous frame.

The emulator is expected to maintain an instruction_history_t buffer that is
used during the emulation. It must be large enough to handle a frame's worth of
instructions. When the frame is complete, this internal buffer is reallocated
to truncate any extra space and pack it as small as possible, and the pointer
to this reallocated structure is returned as the value of the function.

.. code-block::

   instruction_history_t *lib6502_next_frame(instruction_history_t *original, instruction_history_t *input);

The ``original`` argument is used for debugging when the user has changed a
value mid-frame. The instruction history can be modified by inserting some Type
8x records before a Type 10 record. Once the first difference occurs between
the original history list and the output history list, subsequent user input
found in the modified original list will be ignored. The act of inserting input
changes invalidates the remainder of the original instruction history.

After inserting user input and running the frame, the output instruction
history will have the user input records inserted into the instruction history.
This new output history can also be used as the original history to regenerate
this frame, and the output will be identical to itself. Additional user inputs
may even be inserted into this new output history as well, though subject to
the above that history is invalidated after new user input. Should the user
input be inserted after other user input instead of before, only the portion of
the instruction history after the insert will be invalidated, keeping the prior
user input.

The ``input`` argument can be used to supply user input before processing any
instructions, or can be tied to an instruction number and the input will be
delayed until that instruction count is reached. This can be used in
combination with the ``original`` argument, and the input will be inserted
before the specified instructions in the output instruction history list.
Again, all instruction history after new user input will be invalidated.

The arguments may be ``NULL`` in which case the frame will be processed
normally.


Utility Functions in libdebugger
===================================================

Libdebugger has functions to help process instruction history lists and
generate data useful for postprocessing.

 * calculate the current state of the machine
 * calculate the memory access

Current State
-------------------------------

The current state of the machine at some instruction count is available with:

.. code-block::

   current_state_t *libdebugger_calc_current_state(instruction_history_t *h, int num);

An instruction count of 0 is the state at the beginning of the frame, and -1
will provide the state at the end of the frame. Any positive number will be
clamped to the largest instruction number and the state returned will be the
state of the machine *immediately before that instruction*.

