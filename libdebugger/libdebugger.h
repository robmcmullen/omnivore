#ifndef LIBDEBUGGER_H
#define LIBDEBUGGER_H
#include <stdint.h>

#include "libudis.h"
/* The debugger structure must match the definition in omni8bit/debugger/dtypes.py */

#define MAIN_MEMORY_SIZE (256*256)

#define LIBDEBUGGER_SAVE_STATE_MAGIC 0x6462606c

// macros to save variables to (possibly unaligned, possibly endian-swapped)
// data buffer. NOTE: endian-swappiness not actually handled yet, assuming
// little endian
#define save16(buf, var) memcpy(buf, &var, 2)
#define save32(buf, var) memcpy(buf, &var, 4)
#define save64(buf, var) memcpy(buf, &var, 8)

#define load16(var, buf) memcpy(&var, buf, 2)
#define load32(var, buf) memcpy(&var, buf, 4)
#define load64(var, buf) memcpy(&var, buf, 8)

// header for save state file. All emulators must use a save state format that
// uses this header; must be 128 bytes long to reserve space for future
// compatibilty
typedef struct {
    uint32_t malloc_size; /* size of structure in bytes */
    uint32_t magic; /* libdebugger magic number */
    uint32_t frame_number;
    uint32_t emulator_id; /* unique emulator ID number */

    // Frame input parameters
    uint32_t input_offset; /* number of bytes from start to user input history */
    uint32_t input_size; /* number of bytes in user input history */

    // Frame output parameters
    uint32_t save_state_offset; /* number of bytes from start to save state data */
    uint32_t save_state_size; /* number of bytes in save state data */

    uint32_t video_offset; /* number of bytes from start to video data */
    uint32_t video_size; /* number of bytes in video data */

    uint32_t audio_offset; /* number of bytes from start to audio data */
    uint32_t audio_size; /* number of bytes in audio data */

    uint8_t unused0[80];
} emulator_state_t;

#define INPUT_PTR(buf) ((char *)buf + buf->input_offset)
#define SAVE_STATE_PTR(buf) ((char *)buf + buf->save_state_offset)
#define VIDEO_PTR(buf) ((char *)buf + buf->video_offset)
#define AUDIO_PTR(buf) ((char *)buf + buf->audio_offset)


/* current state of emulator */
typedef struct {  /* 32 bit alignment */
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
    uint8_t ram[MAIN_MEMORY_SIZE]; /* complete 64K of RAM */
    uint8_t access_type[MAIN_MEMORY_SIZE]; /* corresponds to RAM */
} current_state_t;


/* emulator operation record, fits in uint32_t */
typedef struct {
    uint8_t type;
    uint8_t payload1;
    uint8_t payload2;
    uint8_t payload3;
} op_record_t;


// operation history array header, used as first several elements in array of
// uint32_t of size of OP_HISTORY_T_SIZE + max_steps + max_lookup
typedef struct {
    uint32_t num_allocated; /* total number of uint32 in structure, including steps and lookup */
    uint32_t frame_number;
    uint32_t max_records; /* maximum space available for records */
    uint32_t num_records; /* current number of records */
    uint32_t max_lookup; /* max space available for instruction lookup table */
    uint32_t num_lookup; /* current count of instruction lookup table */
} op_history_t;

// number of uint32_t in header before op record space in the instruction
// history array
#define OP_HISTORY_T_SIZE (sizeof(op_history_t) / sizeof(uint32_t))

emulator_state_t *create_emulator_state(int save_size, int input_size, int video_size, int audio_size);

op_history_t *create_op_history(int max_steps, int max_lookup);

void print_op_history(op_history_t *buf);

void clear_op_history(op_history_t *buf);

op_history_t *copy_op_history(op_history_t *src);

/* operation history utility functions */
void op_history_start_frame(op_history_t *buf, uint16_t PC, int frame_number);

void op_history_end_frame(op_history_t *buf, uint16_t PC);

void op_history_add_instruction(op_history_t *buf, uint16_t PC, uint8_t *opcodes, uint8_t count);

void op_history_new_pc(op_history_t *buf, uint16_t PC);

void op_history_opcode_ref_addr(op_history_t *buf, uint16_t addr);

void op_history_branch_taken(op_history_t *buf);

void op_history_branch_not_taken(op_history_t *buf);

void op_history_computed_address(op_history_t *buf, uint16_t addr);

void op_history_read_address(op_history_t *buf, uint16_t addr, uint8_t value);

void op_history_write_address(op_history_t *buf, uint16_t addr, uint8_t value);

void op_history_one_byte_reg(op_history_t *buf, uint8_t reg, uint8_t value);

void op_history_two_byte_reg(op_history_t *buf, uint8_t reg, uint16_t value);


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
#define BREAKPOINT_COUNT_LINES 0x8

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
#define EMU_SCAN_LINE (213)
#define EMU_COLOR_CLOCK (214)
#define EMU_VBI_START (215)  /* transition to VBI */
#define EMU_IN_VBI (216)  /* inside VBI */
#define EMU_VBI_END (217)  /* transition out of VBI */
#define EMU_DLI_START (218)  /* transition to DLI */
#define EMU_IN_DLI (219)  /* inside DLI */
#define EMU_DLI_END (220)  /* transition out of DLI */
#define REG_SR (221)
#define REG_P REG_SR
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

int libdebugger_brk_instruction(breakpoints_t *breakpoints);

int libdebugger_check_breakpoints(breakpoints_t *, op_history_t *, int);

#endif /* LIBDEBUGGER_H */
