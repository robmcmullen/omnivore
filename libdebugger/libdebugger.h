#ifndef LIBDEBUGGER_H
#define LIBDEBUGGER_H
#include <stdint.h>

#include "libudis.h"
/* The debugger structure must match the definition in omni8bit/debugger/dtypes.py */

#define MAIN_MEMORY_SIZE (256*256)

typedef struct {
        int64_t cycles_since_power_on;
        int64_t instructions_since_power_on;
        int64_t cycles_user;
        int64_t instructions_user;
        int32_t frame_number;
        int32_t current_cycle_in_frame;
        int32_t final_cycle_in_frame;
        int32_t current_instruction_in_frame;

        int16_t breakpoint_id;
        int16_t unused1[3];

        /* flags */
        uint8_t frame_status;
        uint8_t use_memory_access;
        uint8_t brk_into_debugger; /* enter debugger on BRK */
        uint8_t unused2[5];

        int64_t unused3[8]; /* 16 x uint64 in header (16*8 bytes) */

        uint8_t memory_access[MAIN_MEMORY_SIZE];
        uint8_t access_type[MAIN_MEMORY_SIZE];
} frame_status_t;

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
#define BREAKPOINT_DISABLED 0x40
#define BREAKPOINT_ERROR 0x80
#define EVALUATION_ERROR 0x81  /* a problem with the postfix definition */
#define STACK_UNDERFLOW 0x82  /* too many operators/not enough values */
#define STACK_OVERFLOW 0x83  /* too many values */

/* breakpoint types */
#define BREAKPOINT_CONDITIONAL 0
#define BREAKPOINT_COUNT_INSTRUCTIONS 0x1
#define BREAKPOINT_COUNT_CYCLES 0x2
#define BREAKPOINT_AT_RETURN 0x3
#define BREAKPOINT_COUNT_FRAMES 0x4
#define BREAKPOINT_INFINITE_LOOP 0x5
#define BREAKPOINT_BRK_INSTRUCTION 0x6
#define BREAKPOINT_PAUSE_AT_FRAME_START 0x7

/* status values returned */
#define NO_BREAKPOINT_FOUND -1

/* NOTE: breakpoint #0 is reserved for stepping the cpu */
typedef struct {
        int32_t num_breakpoints;
        int32_t last_pc; /* allow -1 to signify invalid PC */
        int32_t unused[14];
        int64_t reference_value[NUM_BREAKPOINT_ENTRIES];
        uint8_t breakpoint_type[NUM_BREAKPOINT_ENTRIES];
        uint8_t breakpoint_status[NUM_BREAKPOINT_ENTRIES];
        uint16_t tokens[TOKEN_LIST_SIZE];  /* indexed by breakpoint number * TOKENS_PER_BREAKPOINT */
} breakpoints_t;


/* operation flags */
#define OP_UNARY 0x1000
#define OP_BINARY 0x2000
#define VALUE_ARGUMENT 0x3000

#define OP_MASK 0xf000
#define TOKEN_MASK 0x0fff

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
#define EMU_SCANLINE (213)
#define EMU_COLOR_CLOCK (214)
#define EMU_VBI_START (215)  /* transition to VBI */
#define EMU_IN_VBI (216)  /* inside VBI */
#define EMU_VBI_END (217)  /* transition out of VBI */
#define EMU_DLI_START (218)  /* transition to DLI */
#define EMU_IN_DLI (219)  /* inside DLI */
#define EMU_DLI_END (220)  /* transition out of DLI */
#define NUMBER (301 | VALUE_ARGUMENT)
#define OPCODE_TYPE (302 | VALUE_ARGUMENT)

#define COUNT_INSTRUCTIONS (401 | VALUE_ARGUMENT)
#define COUNT_CYCLES (402 | VALUE_ARGUMENT)

#define OPCODE_READ 1
#define OPCODE_WRITE 2
#define OPCODE_RETURN 4
#define OPCODE_INTERRUPT 8

#define INTERRUPT_NONE 0
#define INTERRUPT_START 1
#define INTERRUPT_PROCESSING 2
#define INTERRUPT_END 3

/* library functions defined in libdebugger.c */

void libdebugger_init_array(breakpoints_t *breakpoints);

typedef int (*cpu_state_callback_ptr)(uint16_t token, uint16_t addr);

typedef int (*emu_frame_callback_ptr)(frame_status_t *output, breakpoints_t *breakpoints, emulator_history_t *entry);

int libdebugger_brk_instruction(breakpoints_t *breakpoints);

int libdebugger_check_breakpoints(breakpoints_t *, frame_status_t *, cpu_state_callback_ptr, int);

int libdebugger_calc_frame(emu_frame_callback_ptr calc, uint8_t *memory, frame_status_t *output, breakpoints_t *breakpoints, emulator_history_t *history);

#endif /* LIBDEBUGGER_H */
