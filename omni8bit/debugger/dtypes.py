# Debugger breakpoint definition
import numpy as np

DEBUGGER_COMMANDS_DTYPE = np.dtype([
    ("num_breakpoints", np.uint8),
    ("num_watchpoints", np.uint8),

    ("breakpoint_address", np.uint16, 256),
    ("breakpoint_status", np.uint8, 256),

    ("watchpoint_term", np.uint16, 16384),
    ("watchpoint_status", np.uint8, 256),
    ("watchpoint_index", np.uint16, 256),
    ("watchpoint_length", np.uint8, 256),
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
EVALUATION_ERROR = 3  # a problem with the postfix definition
INDEX_OUT_OF_RANGE = 4  # a watchpoint tried to go beyond the watchpoint_term array size
TOO_MANY_TERMS = 5  # an single watchpoint can only have 255 terms
STACK_UNDERFLOW = 6  # too many operators/not enough values
STACK_OVERFLOW = 7  # too many values
