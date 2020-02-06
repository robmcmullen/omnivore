#ifndef LIBEMU_OP_HISTORY_H
#define LIBEMU_OP_HISTORY_H
#include <stdint.h>


#define MAIN_MEMORY_SIZE (256*256)

#define CURRENT_STATE_JMP 1
#define CURRENT_STATE_BRANCH 2
#define CURRENT_STATE_BRANCH_TAKEN 4
#define CURRENT_STATE_COMPUTED_ADDR 8
#define CURRENT_STATE_MEMORY_READ 0x10
#define CURRENT_STATE_MEMORY_WRITE 0x20
#define CURRENT_STATE_BYTE_REGISTER 0x40
#define CURRENT_STATE_WORD_REGISTER 0x80
#define CURRENT_STATE_OPCODE_ADDR 0x100
#define CURRENT_STATE_OTHER_DISASSEMBLER_TYPE 0x8000

/* current state of emulator */
typedef struct {  /* 32 bit alignment */
    uint32_t frame_number;
    int32_t line_number;

    /* instruction */
    uint16_t pc; /* special two-byte register for the PC */
    uint16_t opcode_ref_addr; /* address referenced in opcode */
    uint8_t instruction_length; /* number of bytes in current instruction */
    uint8_t instruction[255]; /* current instruction */

    /* flags */
    uint16_t flag;
    uint8_t nominal_disassembler_type;
    uint8_t current_disassembler_type;

    /* result of instruction */
    uint16_t computed_addr; /* computed address after indirection/indexing */
    uint8_t register_used;
    uint8_t unused;

    uint8_t reg_byte[256]; /* single byte registers */
    uint16_t reg_word[256]; /* two-byte registers */
    uint8_t memory[MAIN_MEMORY_SIZE]; /* complete 64K of RAM */
    uint8_t access_type[MAIN_MEMORY_SIZE]; /* corresponds to RAM */
} current_state_t;


/* emulator operation record, fits in uint32_t */
typedef struct {
    uint8_t type;
    uint8_t num;
    union {
        uint8_t byte[2];
        uint16_t word;
    } payload;
} op_record_t;


// operation history array header, used as first several elements in array of
// uint32_t of size of OP_HISTORY_T_SIZE + max_steps + max_line_to_record +
// max_byte_to_line
typedef struct {
    uint32_t malloc_size; /* total number of bytes in structure, including steps and lookup */
    uint32_t frame_number;
    uint32_t max_records; /* maximum space available for records */
    uint32_t num_records; /* current number of records */
    uint32_t max_line_to_record; /* max for line-to-record lookup table */
    uint32_t num_line_to_record; /* current count */
    uint32_t max_byte_to_line; /* max for byte-to-line lookup table */
    uint32_t num_byte_to_line; /* current count */
} op_history_t;

// number of uint32_t in header before op record space in the instruction
// history array
#define OP_HISTORY_T_SIZE (sizeof(op_history_t) / sizeof(uint32_t))

op_history_t *create_op_history(int max_steps, int max_line_to_record, int max_byte_to_line);

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

op_record_t *get_record_from_line_number(op_history_t *buf, int num);

int eval_operation(current_state_t *current, op_record_t *op);

#endif /* LIBEMU_OP_HISTORY_H */
