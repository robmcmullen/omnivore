========================================================================
LibEMU: Omnivore Multi-Emulator Debugging Architecture Code Design
========================================================================


Overview
==========

The Omnivore Multi-Emulator Debugging Architecture (LibEMU) is a frame-based
emulator architecture that implements a full debugger based on history
generated at each CPU instruction within each frame. This frees emulators from
having to process breakpoints within the emulation code:

 * simplifying and speeding up emulator code by removing debugging
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

 * record changes in emulator state after each instruction, saved in a history
   of operations
 * change emulator state in mid-frame for user debugging

The debugger will only be able to break on data saved in the operation history,
anything not recorded in the history won't be available.


Debugging Process
-------------------------

Since the emulator doesn't handle breakpoints itself, it relies on the front-
end to handle any breakpoints. The emulator will generate the emulation for an
entire frame to produce the instruction operation history (**op history**) for
that frame, and return this data to the front-end.

If no breakpoints are defined, the front-end displays the results of the frame
(i.e. displaying the emulated screen, playing any sound generated during this
frame, etc.) and continues to process the next frame. Because the emulator
itself is not checking breakpoints at every instruction, the emulator code will
likely be faster than a typical emulator since it does not have to loop through
all breakpoints at each instruction.

If any breakpoints are defined, the front-end then steps through the
op history seeing if any breakpoint conditions are met. Because the
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
through the op history as if the emulator was performing the actions
of the current instruction in the history. The op history contains all
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


Emulator State Limitations
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
built from the op history, the emulator state at any point in history
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


Modifications to Emulation During Debugging
----------------------------------------------------

The emulator is only capable of generating complete frames, so debugging would
be limited to observation of the instructions generated within the frame if
changes to the emulator state were only allowed at frame boundaries.

In order to make changes to the emulator state in the middle of a frame, the
emulator needs to be modified to accept a user change at a certain step. But,
since the user can't actually break the emulator in the middle of the frame,
the change and the step at which the change happens must be supplied to the
emulator at the start of a new frame.

Because more than one change may be requested by the user, a list of changes
and steps at which each change is applied must be generated by the
front-end. This list is supplied to the emulator when the frame is re-run. The
emulator will regenerate the frame, and up until the first change will produce
an identical op history. Once the step number matches the count
in the change list and before it executes the next instruction, the emulator
will update its state as specified, then resume executing instructions.

The op history will diverge from the original history, starting at the
first op history count containing an emulation state change. The
front-end will present the results to the user, and because a single emulation
frame is a cheap operation, it should appear to the user as if this debugger
were operating as a traditional debugger.


Emulator Development
===============================

One of the advantages of LibEMU is that emulators for multiple CPUs can be
created, and the same UI can be used to debug the code. This means that the
emulators must be created that have a common interface. Because the UI is
designed to be in Python, there must be some bridge code between the emulator
and the high level code.

The emulator itself is expected to be written in C because it must generate
frames quickly. The low-level interface is the bridge between the high-level
Python and the low-level C code, and is written in Cython. The Python UI then
deals with the low-level interface for each emulator, but only has to deal with
emulator specific code to display audio and video, not to display CPU
instructions or perform debugging functions.

Data Types
--------------------



Emulator Output Data
~~~~~~~~~~~~~~~~~~~~~~~~~~

The emulator must produce two types of output, one specific to the emulator
and one using a LibEMU data structure:

 * frame output, including:
   * some opaque data consisting of the emulator save state that can be used to restore the machine state to the same condition as the end of this frame
   * audio data in a TBD format
   * video data in some emulator-specific format
 * op history

The common code in LibEMU uses the op history to produce the
current machine state at any instruction within that frame, and this is what
the UI uses to display and step through the CPU history.

Creating the Frame Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The frame output is a data structure that is emulator-specific, and is opaque
to the LibEMU code. It is partially opaque to the UI: the video and audio
portion of the save state are used to draw the screen and produce sound, but
the machine state data is intended to be opaque.

To display the CPU state and the instructions, the UI uses the LibEMU code
to generate the current machine state at a particular instruction in the op
history, and that is what the UI uses to display and step through the opcodes.

The opaque portion of the frame output is used by the emulator to restore its
state, so only the low-level emulator code is required to know its format.


Creating the Op History
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

<stuff>



Low Level Emulator Code
-------------------------------

Each emulator must be able to generate complete frames, save and restore
emulator state, and generate data required for the LibEMU interface.


Interface to Low Level Code
--------------------------------------

The low level interface is the Cython code providing the bridge between the
Python UI and the C code providing fast emulation.

The Cython code must provide several functions:

 * ``init_emulator``
 * ``cold_start``
 * ``next_frame``
 * ``export_steps``
 * ``export_frame``
 * ``import_frame``

``init_emulator``
~~~~~~~~~~~~~~~~~~~~~~~~~

A one-time call provided to allow the emulator to perform some initial setup
tasks before any frame generation takes place. Some emulators may not require
this, but it is provided in case it is needed.

``cold_start``
~~~~~~~~~~~~~~~~~~~~~~~~

Generates "frame zero" of emulation, which returns emulator to initial state
(as it was after the call to ``init_emulator``), and performs the setup tasks
described in the input list argument. The save state resulting from this
function is used as the input for the first real frame of emulation.


``next_frame``
~~~~~~~~~~~~~~~~~~~~~~~~

Performs one emulation frame, optionally taking an argument that will provide
user inputs at specified points in the operation history. Without any argument,
the emulator will continue the current operation of the CPU without any user
input.

The optional argument can be one of two things. First, it may be a list of user
input changes, where the user inputs (keypresses, joystick moves, etc.) are
inserted into the emulation at the instruction locations specified in the
list.

Second, the optional argument may a modified version of the op history
previously generated for this frame. User input changes may be inserted into
this op history, which causes the emulator to regenerate the frame and
using the user input to change the emulation mid-frame. This is the way to
simulate a normal debugger that can step by instructions and modify the
emulator state regardless of where the instruction is. Here, because we can
only generate complete frames, is the way that we can force the emulator to act
like a traditional emulator that has full control at every CPU step.

The emulator will then generate a new op history as it processes a
frame containing user input changes. The new op history will track
with the user input op history until the generated op history
diverges from the input history due to the user input producing a change in
emulation.

Once a divergence is detected, further user input is ignored under the
assumption that any remaining input was applicable to the conditions in the
emulator related to the old history, not the history currently being generated.
Since emulators are required to be deterministic, any change in emulation must
be the result of the user input.


something has changed, won't have meaning in the new history. won't apply to
the new history because the instructions will change between this point and the
next user input. An user input change later on in the input op history
may not have bearing once the emulation changes, so it's

``export_steps``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Utility function to export the instruction steps taken to create the final
state of this frame. The instruction steps are what is used to display the
state of the emulator at any opcode within the frame.

``export_frame``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Utility function to export the current emulator state to a new array. As the
emulator only processes complete frames, this means the state of the emulator
can only be saved will be after the end of a frame.

If there is any user input history for the frame, the save state must include
that as well in order that it be correctly regenerated if the save state is
restored and the frame computed again.

``import_frame``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Utility function to import the current emulator state from an array previously
created from a call to ``export_frame``. The emulator will be returned to
condition at the end of the frame when the state was saved.


User Interface
==========================

The low level code 


Frame History: The Sequence of Frames
---------------------------------------------------------

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



Displaying the Current Emulator State
=============================================

Presenting the user with the op history involves stepping through all
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
emulator, visualizations of memory accesses based on the op history,
or internal status of any memory-mapped hardware or coprocessors (like the GTIA
or ANTIC in the atari800 emulator). This is not an exhaustive list; many other
features are possible using the op history data.

To see the machine state at any point in the op history, a data
structure is needed to hold the successive application of the deltas contained
in the op history. An example of this structure is defined as follows:

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
      uint8_t access_type[256*256]; /* corresponds to RAM */
   } current_state_t;

Because the op history will have variable numbers of records for each
instruction, a lookup table is generated as a post-processing step by
LibEMU, after the emulator generates a frame. It is a simple list, indexed
by line number to be displayed in the UI, pointing to the index in the
op history list of the :ref:`Type 01 record <type01>` for the
instruction.

.. code-block::

   uint32_t instruction_lookup[...]; /* allocated */



Sample op history
-----------------------------------

This example is an op history for a 6502 emulator:

.. csv-table:: op history
   :widths: 10,10,10,10,10,40

   Entry, Record Type, B1, B2, B3, Description
   0, 10,00,80,00,PC = $8000, 0 bytes in the instruction: UI line #0
   1, 21,01,00,00,Frame #1 start
   2, 10,00,80,03,PC = $8000, 3 bytes in the instruction: UI line #1
   3, 20,00,60,00,INSTRUCTION: JSR $6000
   4, 03,ff,01,02,store low byte of return addr on stack
   5, 03,fe,01,80,store high byte of return addr on stack
   6, 01,04,fd,00,move stack pointer down by 2
   7, 06,00,60,00,PC changed to $6000
   8, 10,00,60,02,PC = $6000, 2 bytes in the instruction: UI line #2
   9, a9,00,00,00,INSTRUCTION: LDA #$00
   10, 01,01,00,00,register A = 0
   11, 01,05,02,00,status register = $02 (Z = 1)
   12, 10,02,60,02,PC = $6002, 2 bytes in the instruction: UI line #3
   13, 85,08,00,00,INSTRUCTION: STA $08
   14, 03,08,00,00,$0 stored in address $0008
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
   37, 03,08,00,08,write value 8 to $08
   38, 10,09,80,00,PC = $8009, 0 bytes in the instruction: UI line #9
   39, 2e,02,00,00,NMI start: DLI
   40, 03,ff,01,09,store low byte of return addr on stack
   41, 03,fe,01,80,store high byte of return addr on stack
   42, 03,fd,01,02,store status register on stack
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
      uint8_t ram[65536];
      uint8_t access_type[65536];
   } current_state_t;

This structure is filled at the beginning of the frame and modified by the
op history deltas as instructions are processed for display in the UI. At the beginning of the frame, the emulator state is copied directly into the structure. At power-on, this data might be:

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
   memcpy(c.ram, emulator_ram, 65536);
   memset(c.access_type, 0, 65536);

As instructions are processed by the UI for display, the deltas are used to
modify this structure. Using the example above, the UI uses the
``instruction_lookup`` array to determine which history entry starts the
definition for the text display. For the example above, it contains these
values:

   0, 2, 8, 11, 15, 18, 26, 33, 38, 46, 50, 55, 59, 61, 64

which maps the line number that will hold the text representation of this
instruction to the position in the op history array of the Type 10
record (or Type 0 record in the case of the very first entry).

Index 0 of this array points to the frame start entry:

.. csv-table:: op history, index 0 - 1
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
``instruction_lookup`` array points to this sequence of deltas:

.. csv-table:: op history, index 2 - 7
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
   c.access_type[0x1ff] = ACCESS_TYPE_WRITE;
   c.ram[0x1fe] = 0x80;
   c.access_type[0x1fe] = ACCESS_TYPE_WRITE;
   c.access_type[0x8000] = ACCESS_TYPE_EXECUTE;
   c.access_type[0x8001] = ACCESS_TYPE_EXECUTE;
   c.access_type[0x8002] = ACCESS_TYPE_EXECUTE;

and is cached (if caching is implemented) as the emulator state for UI line #1.


Creating op history in Emulator
===============================================

The LibEMU code includes some convenience functions to create op history. At
the start of an emulation frame, a call to:

.. code-block::

   step_history_t *create_instruction_history(int max_delta, int max_ui_lines);

will return data storage space for the op history that will be built
as the emulation processes opcodes during the frame. The ``step_history_t``
structure is defined as:

.. code-block::

   typedef struct {
      uint32_t frame_number;
      uint32_t max_delta;
      uint32_t num_delta; /* current count of deltas */
      uint32_t max_instruction_lookup;
      uint32_t num_instruction_lookup; /* current count of ui lines */
   } step_history_t;

The parameters ``max_delta`` and ``max_instruction_lookup`` is not precisely
known at the start of any emulation frame because opcodes take different number
of clock cycles. So, it is advisable to overestimate the number during this
call. The code actually reuses the same data for every emulation frame, and the
call to:

.. code-block::

   step_history_t *copy_instruction_history(step_history_t *source);

will create a copy of the working op history that is sized to exactly
hold the data. It will look at the array sizes determined by ``num_delta`` and
``num_instruction_lookup`` and create allocated sizes for ``delta`` and
``instruction_lookup`` that exactly match those numbers.

Internally, the code allocates one block of memory for the size of the
``step_history_t`` structure *plus* the sizes of the deltas and ui line lookup
table, and partitions that into 3 areas with the delta and ui line lookup
pointers using addresses within this allocation.

For example, in a 64 bit system, ``sizeof(step_history_t)`` is 20 bytes, and if
there are 10,000 entries in the ``delta`` array and 2000 in the
``instruction_lookup`` array, the allocation would be ``20 + 10000*4 + 2000*4``
or 48020 bytes in a single array:

   +----+---------------------------------------+-------------+
   | 20 |                 40000                 |    8000     |
   +----+---------------------------------------+-------------+

The ``delta`` pointer would then point to 20 bytes beyond the start of the
array, and the ``instruction_lookup`` points to 40020 bytes after the start of the
array.

The call to ``finalize_instruction_history`` uses the counts of the entries in
both allocated arrays to allocate a new block of memory with no wasted space.
Using the example above, if ``num_delta = 4055`` and ``num_instruction_lookup =
822``,  the exactly-fitted allocation would be ``20 + 4055*4 + 822*4`` or 19528
bytes:

   +----+-------------------+------+
   | 20 |       16220       | 3288 |
   +----+-------------------+------+


Emulation Frame Storage
=================================

An emulation frame consists of the save state of the machine, the video and
audio output resulting from that frame, and the exactly-fitted
``step_history_t`` array as described above.

All this data is from the *end* of the frame, meaning it is the state of the
machine when the frame is complete. To re-run the frame, the machine state from
the *previous* frame must be loaded, then the instructions making up this frame
executed. In other words, the instructions making up the ``step_history_t``
array transform the machine state from the previous frame's end state to the
current frame's end state.

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

With LibEMU, the emulator only processes full frames and leaves all post-
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

   int lib6502_export_frame(lib6502_state_t *buf);

Import Save State
--------------------------

This function restores the emulator internal state using the previously
imported buffer exported through the function above.

.. code-block::

   int lib6502_import_frame(lib6502_state_t *buf);

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

The emulator is expected to maintain an step_history_t buffer that is used
during the emulation. It must be large enough to handle a frame's worth of
instructions. When the frame is complete, this internal buffer is reallocated
to truncate any extra space and pack it as small as possible, and the pointer
to this reallocated structure is returned as the value of the function.

.. code-block::

   step_history_t *lib6502_next_frame(step_history_t *original, step_history_t *input);

The ``original`` argument is used for debugging when the user has changed a
value mid-frame. The op history can be modified by inserting some Type
8x records before a Type 10 record. Once the first difference occurs between
the original history list and the output history list, subsequent user input
found in the modified original list will be ignored. The act of inserting input
changes invalidates the remainder of the original op history.

After inserting user input and running the frame, the output instruction
history will have the user input records inserted into the op history.
This new output history can also be used as the original history to regenerate
this frame, and the output will be identical to itself. Additional user inputs
may even be inserted into this new output history as well, though subject to
the above that history is invalidated after new user input. Should the user
input be inserted after other user input instead of before, only the portion of
the op history after the insert will be invalidated, keeping the prior
user input.

The ``input`` argument can be used to supply user input before processing any
instructions, or can be tied to an instruction number and the input will be
delayed until that step number is reached. This can be used in
combination with the ``original`` argument, and the input will be inserted
before the specified instructions in the output op history list.
Again, all op history after new user input will be invalidated.

The arguments may be ``NULL`` in which case the frame will be processed
normally.


Utility Functions in LibEMU
===================================================

LibEMU has functions to help process op history lists and generate data useful
for postprocessing.

 * calculate the current state of the machine
 * calculate the memory access statistics for the frame

Current State
-------------------------------

The current state of the machine at some step number is available with:

.. code-block::

   void libemu_calc_current_state(current_state_t *buf, step_history_t *h, int step_number);

An step number of 0 is the state at the beginning of the frame, and -1 will
provide the state at the end of the frame. Any positive number will be clamped
to the largest instruction number and the state returned will be the state of
the machine *immediately before that instruction*.


Memory Access
-------------------------------

The memory access statistics is an array that parallels the emulator's RAM,
describing each type of memory access. For each instruction that accesses
memory, either by reading it, writing to it, being executed, or other emulator-
specific actions (like being used for display memory or a display list in the
atari800 emulator), a flag is stored referencing that memory location.

The flags are defined in libemu.h:

.. code-block::

   /* lower 4 bits: bit access flags */
   #define ACCESS_TYPE_READ 1
   #define ACCESS_TYPE_WRITE 2
   #define ACCESS_TYPE_EXECUTE 4

   /* upper 4 bits: type of access, not a bit field */
   #define ACCESS_TYPE_VIDEO 0x10
   #define ACCESS_TYPE_DISPLAY_LIST 0x20
   #define ACCESS_TYPE_CHBASE 0x30
   #define ACCESS_TYPE_PMBASE 0x40
   #define ACCESS_TYPE_CHARACTER 0x50
   #define ACCESS_TYPE_HARDWARE 0x60

The memory access array is defined in the ``current_state_t`` structure and is
updated during calls to ``libemu_calc_current_state``.

The front-end can use the memory access type to create a graphical display
showing the areas of memory used in this frame of emulation.


Debugging with LibEMU
========================================

Finally we get to debugging! This design allows any emulator that implements
the LibEMU op history to use the same debugging code. That means
the same user interface can be applied across emulators, simplifying
development on multiple platforms by not being dependent on individual
emulators with their unique debugging commands.

Debugging works by examining the ``current_state_t`` structure to see if any
breakpoint conditions are true. Breakpoints are checked at every Type 10
record, which checks if the previous instruction caused a change or the PC
matches the PC in the Type 10 record. This is how regular debuggers work,
except instead of checking the op history after the fact, they are
checking as the emulator processes the instructions.

For each frame, the op history contains the ``instruction_lookup``
array which allows stepping by instruction. This array holds the locations of
all Type 10 records in the op history. At the start of the frame,
``instruction_lookup[0]`` is zero, which is the signal to populate the current
state from the save state from the previous frame. Any deltas are applied to
reach the history entry just before ``instruction_lookup[1]`` and the
breakpoint conditions are checked. If no breakpoint matches, the deltas
starting at ``instruction_lookup[1]`` are applied until the entry immediately
before ``instruction_lookup[2]`` and the breakpoint conditions are checked
there. And so on: the deltas are applied until the entry just before the next
Type 10 record and the breakpoint conditions are checked.

If a breakpoint condition matches, control returns to the user program with the
breakpoint ID that matched, the instruction number, and the current state of
the machine so the UI can be updated to show the breakpoint.

The breakpoint match means that the currently processed instruction has met
some condition, so breakpoints don't occur before an instruction, they occur
after. For example, breaking on a read of the address $8000 in the following
code:

.. code-block::

   6000  LDA $7fff
   6003  STA $3fff
   6006  LDA $8000
   6009  STA $4000

would occur after the ``LDA $8000`` command has executed and changed the
machine's current state to reflect the read of the $8000 address. The PC would
show $6009, but that instruction (the ``STA $4000``) will not yet have
executed.


Front End Development
=====================================

The front-end driving the emulator will have to maintain the array (or tree) of
frame save states. As the emulator generates a frame, it returns the save state
information for that frame and any output generated (video, audio).

Frame 0 is the initial condition of the emulator, including the configuration,
before any instructions are processed. The save state at the end of frame 0 is
used as input for frame 1, which is the first frame that processes
instructions. (Essentially, the CPU is turned on with the first instruction of
frame 1.) At the end of the frame, the front- end must store the save state for
frame 1, which is then used as the input for frame 2. And so on.

The data stored for a frame is the results of processing that frame, so the UI
should be clear that save state for frame 1 is the internal state of the
emulator at the *end* of frame 1. The front-end must also make it clear that
restoring the emulator to frame 1 restores the emulator to the condition at the
*end* of frame 1. Resuming emulation from there means the CPU starts from the
end of frame 1, which is equivalent to starting from frame 2.

The video and audio saved at the end of the frame are the only outputs that
should be used from the save state to display to the user. Everything else
displayed it the UI (all other data displays) should use the
``current_state_t`` array as produced by the call to
``libemu_calc_current_state``. Calling that function with an instruction
count of ``-1`` will produce the current state at the end of the frame and is
the one place after the start of the op history where stepping through
the entire history is not necessary; the ``current_state_t`` will be populated
directly from the save state.

The current state array is allocated by the front end and the pointer passed to
``libemu_calc_current_state`` so that a Segment can be defined and viewers
can directly access that data as it is updated.

