# Debugger breakpoint definition
import numpy as np

MAIN_MEMORY_SIZE = 1<<16

FRAME_STATUS_DTYPE = np.dtype([
    ("cycles_since_power_on", np.uint64),
    ("instructions_since_power_on", np.uint64),
    ("cycles_user", np.uint64),
    ("instructions_user", np.uint64),
    ("frame_number", np.uint32),
    ("current_cycle_in_frame", np.uint32),
    ("final_cycle_in_frame", np.uint32),
    ("current_instruction_in_frame", np.uint32),

    ("breakpoint_id", np.int16),
    ("unused1", np.uint16, 3),

    ("frame_status", np.uint8),
    ("use_memory_access", np.uint8),
    ("brk_into_debugger", np.uint8),
    ("unused2", np.uint8, 5),

    ("unused3", np.uint64, 8), # fill header to 128 bytes

    ("memory_access", np.uint8, MAIN_MEMORY_SIZE),
    ("access_type", np.uint8, MAIN_MEMORY_SIZE),
])

ACCESS_TYPE_READ = 1
ACCESS_TYPE_WRITE = 2
ACCESS_TYPE_EXECUTE = 4
ACCESS_TYPE_VIDEO = 8
ACCESS_TYPE_DISPLAY_LIST = 16

default_access_type_colors = {
    0: (0, 0, 0),
    ACCESS_TYPE_READ: (0, 255, 0),
    ACCESS_TYPE_WRITE: (255, 0, 0),
    ACCESS_TYPE_EXECUTE: (255, 255, 0),
    ACCESS_TYPE_VIDEO: (0, 0, 255),
    ACCESS_TYPE_DISPLAY_LIST: (255, 0, 255),
}


NUM_BREAKPOINT_ENTRIES = 256
TOKENS_PER_BREAKPOINT = 64
TOKEN_LIST_SIZE = (NUM_BREAKPOINT_ENTRIES * TOKENS_PER_BREAKPOINT)

# Breakpoint #0 is used internally for stepping the CPU
DEBUGGER_COMMANDS_DTYPE = np.dtype([
    ("num_breakpoints", np.uint32),
    ("last_pc", np.int32),
    ("unused", np.uint32, 14),
    ("reference_value", np.int64, NUM_BREAKPOINT_ENTRIES),
    ("breakpoint_type", np.uint8, NUM_BREAKPOINT_ENTRIES),
    ("breakpoint_status", np.uint8, NUM_BREAKPOINT_ENTRIES),
    ("tokens", np.uint16, TOKEN_LIST_SIZE),
])

# Breakpoints are address of PC to break at before executing code at that
# address. Breakpoints are only evaluated if the corresponding
# `breakpoint_status` value is BREAKPOINT_ENABLED. `num_breakpoints` serves as
# a speed optimization: the `breakpoints` list will not be scanned past that
# number of entries. There are a maximum of 256 breakpoint entries.

# Watchpoints use the same status values as breakpoints, but as they are
# variable length include an index into the watchpoints list and the length in
# words in `watchpoint_index` and `watchpoint_length` respectively.
# `num_watchpoints` serves the same purpose as `num_breakpoints`. There are a
# maximum of 256 watchpoint entries. The list of words pointed to by
# `watchpoint_index` are mathematical terms in postfix notation, the evaluation
# of which yields a 16 bit unsigned value, interpreted as a true or false
# condition whether the watchpoint should be triggered. True is a non-zero
# value and false is zero.

# Breakpoint/watchpoint status values. For watchpoints, the status value can be
# changed by the watchpoint processor if it finds a problem in a rule. Note
# that watchpoints are only processed when their status is BREAKPOINT_ENABLED,
# so it is up to the calling program to change the state back to this after an
# error is corrected.

BREAKPOINT_EMPTY = 0
BREAKPOINT_ENABLED = 0x20
BREAKPOINT_DISABLED = 0x40
BREAKPOINT_ERROR = 0x80
EVALUATION_ERROR = 0x81  # a problem with the postfix definition
STACK_UNDERFLOW = 0x82  # too many operators/not enough values
STACK_OVERFLOW = 0x83  # too many values

# breakpoint types
BREAKPOINT_CONDITIONAL = 0
BREAKPOINT_COUNT_INSTRUCTIONS = 0x1
BREAKPOINT_COUNT_CYCLES = 0x2
BREAKPOINT_AT_RETURN = 0x3
BREAKPOINT_COUNT_FRAMES = 0x4
BREAKPOINT_INFINITE_LOOP = 0x5


# contitional breakpoint definitions

OP_UNARY = 0x1000
OP_BINARY = 0x2000
VALUE_ARGUMENT = 0x3000

OP_MASK = 0xf000
TOKEN_MASK = 0x0fff

# operations
END_OF_LIST = 0
OP_BITWISE_AND = (102 | OP_BINARY)
OP_BITWISE_NOT = (103 | OP_UNARY)
OP_BITWISE_OR = (104 | OP_BINARY)
OP_DIV = (105 | OP_BINARY)
OP_EQ = (106 | OP_BINARY)
OP_EXP = (107 | OP_BINARY)
OP_GE = (108 | OP_BINARY)
OP_GT = (109 | OP_BINARY)
OP_LE = (110 | OP_BINARY)
OP_LOGICAL_AND = (111 | OP_BINARY)
OP_LOGICAL_NOT = (112 | OP_UNARY)
OP_LOGICAL_OR = (113 | OP_BINARY)
OP_LSHIFT = (114 | OP_BINARY)
OP_LT = (115 | OP_BINARY)
OP_MINUS = (116 | OP_BINARY)
OP_MULT = (117 | OP_BINARY)
OP_NE = (118 | OP_BINARY)
OP_PLUS = (119 | OP_BINARY)
OP_RSHIFT = (120 | OP_BINARY)
OP_UMINUS = (121 | OP_UNARY)
OP_UPLUS = (122 | OP_UNARY)
REG_A = (201)
REG_X = (202)
REG_Y = (203)
REG_S = (204)
REG_N = (205)
REG_V = (206)
REG_B = (207)
REG_D = (208)
REG_I = (209)
REG_Z = (210)
REG_C = (211)
REG_PC = (212)
REG_SP = REG_S
EMU_SCANLINE = (213)
EMU_COLOR_CLOCK = (214)
EMU_VBI_START = (215)  # transition to VBI
EMU_IN_VBI = (216)  # inside VBI
EMU_VBI_END = (217)  # transition out of VBI
EMU_DLI_START = (218)  # transition to DLI
EMU_IN_DLI = (219)  # inside DLI
EMU_DLI_END = (220)  # transition out of DLI
NUMBER = (301 | VALUE_ARGUMENT)
OPCODE_TYPE = (302 | VALUE_ARGUMENT)

COUNT_INSTRUCTIONS = (401 | VALUE_ARGUMENT)
COUNT_CYCLES = (402 | VALUE_ARGUMENT)

OPCODE_READ = 1
OPCODE_WRITE = 2
OPCODE_RETURN = 4
OPCODE_INTERRUPT = 8
