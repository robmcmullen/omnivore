#ifndef LIBDEBUGGER_H
#define LIBDEBUGGER_H
#include <stdint.h>

/* The debugger structure must match the definition in omni8bit/debugger/dtypes.py */

typedef struct {
        uint64_t cycles_since_power_on;
        uint64_t instructions_since_power_on;
        uint32_t frame_number;
        uint32_t current_cycle_in_frame;
        uint32_t final_cycle_in_frame;
        uint32_t current_instruction_in_frame;

        uint8_t frame_status;
        uint8_t breakpoint_id;
        uint8_t unused1;
        uint8_t unused2;
} frame_status_t;


#define NUM_BREAKPOINT_ENTRIES 256
#define TOKENS_PER_BREAKPOINT 64
#define TOKEN_LIST_SIZE (NUM_BREAKPOINT_ENTRIES * TOKENS_PER_BREAKPOINT)

/* frame status values */
#define FRAME_INCOMPLETE 0
#define FRAME_FINISHED 1
#define FRAME_BREAKPOINT 2

/* breakpoint/watchpoint status values */
#define BREAKPOINT_EMPTY 0

#define BREAKPOINT_ENABLED 0x20
#define BREAKPOINT_COUNT_INSTRUCTIONS 0x21
#define BREAKPOINT_COUNT_CYCLES 0x22

#define BREAKPOINT_DISABLED 0x40

#define BREAKPOINT_ERROR 0x80
#define EVALUATION_ERROR 0x81  /* a problem with the postfix definition */
#define STACK_UNDERFLOW 0x82  /* too many operators/not enough values */
#define STACK_OVERFLOW 0x83  /* too many values */

/* status values returned */
#define NO_BREAKPOINT_FOUND -1

/* NOTE: breakpoint #0 is reserved for stepping the cpu */
typedef struct {
        int num_breakpoints;
        uint8_t breakpoint_status[NUM_BREAKPOINT_ENTRIES];
        uint16_t tokens[TOKEN_LIST_SIZE];  /* indexed by breakpoint number * TOKENS_PER_BREAKPOINT */
} breakpoints_t;


/* operation flags */
#define OP_BINARY 0x8000
#define OP_UNARY 0x4000
#define VALUE_ARGUMENT 0x2000
#define TOKEN_FLAG 0x0fff

/* operations */
#define END_OF_LIST 0
#define OP_BITWISE_AND (102 | OP_BINARY)
#define OP_BITWISE_NOT (103 | OP_UNARY)
#define OP_BITWISE_OR (104 | OP_BINARY)
#define OP_DIV (105 | OP_BINARY)
#define OP_EQ (106 | OP_BINARY)
#define OP_EXP (107 | OP_BINARY)
#define OP_GE (108 | OP_BINARY)
#define OP_GT (109 | OP_BINARY)
#define OP_LE (110 | OP_BINARY)
#define OP_LOGICAL_AND (111 | OP_BINARY)
#define OP_LOGICAL_NOT (112 | OP_UNARY)
#define OP_LOGICAL_OR (113 | OP_BINARY)
#define OP_LSHIFT (114 | OP_BINARY)
#define OP_LT (115 | OP_BINARY)
#define OP_MINUS (116 | OP_BINARY)
#define OP_MULT (117 | OP_BINARY)
#define OP_NE (118 | OP_BINARY)
#define OP_PLUS (119 | OP_BINARY)
#define OP_RSHIFT (120 | OP_BINARY)
#define OP_UMINUS (121 | OP_UNARY)
#define OP_UPLUS (122 | OP_UNARY)
#define REG_A (201)
#define REG_X (202)
#define REG_Y (203)
#define REG_S (204)
#define REG_N (205)
#define REG_V (206)
#define REG_B (207)
#define REG_D (208)
#define REG_I (209)
#define REG_Z (210)
#define REG_C (211)
#define REG_PC (212)
#define REG_SP REG_S
#define NUMBER (301 | VALUE_ARGUMENT)

#define COUNT_INSTRUCTIONS (401 | VALUE_ARGUMENT)
#define COUNT_CYCLES (402 | VALUE_ARGUMENT)

/* library functions defined in libdebugger.c */

void libdebugger_init_array(breakpoints_t *breakpoints);

typedef int (*cpu_state_callback_ptr)(uint16_t token, uint16_t addr);

typedef int (*emu_frame_callback_ptr)(frame_status_t *output, breakpoints_t *breakpoints);

int libdebugger_check_breakpoints(breakpoints_t *breakpoints, int cycles, cpu_state_callback_ptr get_emulator_value);

int libdebugger_calc_frame(emu_frame_callback_ptr calc, frame_status_t *output, breakpoints_t *breakpoints);

#endif /* LIBDEBUGGER_H */
