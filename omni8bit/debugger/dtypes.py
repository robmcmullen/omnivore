# Debugger breakpoint definition
import numpy as np

NUM_BREAKPOINT_ENTRIES = 256
TOKENS_PER_BREAKPOINT = 64
TOKEN_LIST_SIZE = (NUM_BREAKPOINT_ENTRIES * TOKENS_PER_BREAKPOINT)

# Breakpoint #0 is used internally for stepping the CPU
DEBUGGER_COMMANDS_DTYPE = np.dtype([
    ("num_breakpoints", np.uint32),
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
BREAKPOINT_ENABLED = 1
BREAKPOINT_DISABLED = 2
BREAKPOINT_RESERVED = 3
EVALUATION_ERROR = 10  # a problem with the postfix definition
INDEX_OUT_OF_RANGE = 11  # a watchpoint tried to go beyond the watchpoint_term array size
TOO_MANY_TERMS = 12  # an single watchpoint can only have 255 terms
STACK_UNDERFLOW = 13  # too many operators/not enough values
STACK_OVERFLOW = 14  # too many values


# contitional breakpoint definitions

OP_BINARY = 0x8000
OP_UNARY = 0x4000
VALUE_ARGUMENT = 0x2000
TOKEN_FLAG = 0x0fff

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
NUMBER = (301 | VALUE_ARGUMENT)
