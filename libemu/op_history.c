#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libemu/op_history.h"
#define DEBUG_EVAL


/* instruction history utility functions */

op_history_t *create_op_history(int max_records, int max_line_to_record, int max_byte_to_line) {
	op_history_t *buf;
	int num;
	int total_size;

	num = OP_HISTORY_T_SIZE + max_records + max_line_to_record + max_byte_to_line;
	total_size = num * 4; // 4 bytes per uint32
	buf = (op_history_t *)malloc(total_size);
	buf->malloc_size = total_size;
	buf->max_records = max_records;
	buf->max_line_to_record = max_line_to_record;
	buf->max_byte_to_line = max_byte_to_line;
	buf->frame_number = 0;
	clear_op_history(buf);
	return buf;
}

void clear_op_history(op_history_t *buf) {
	buf->num_records = 0;
	buf->num_line_to_record = 0;
	buf->num_byte_to_line = 0;
}

op_history_t *copy_op_history(op_history_t *src) {
	op_history_t *dest;
	uint32_t *src_data;
	uint32_t *dest_data;

	dest = create_op_history(src->num_records, src->num_line_to_record, src->num_byte_to_line);
	dest->num_records = dest->max_records;
	dest->num_line_to_record = dest->max_line_to_record;
	dest->num_byte_to_line = dest->max_byte_to_line;

	/* copy delta entries */
	src_data = (uint32_t *)src + OP_HISTORY_T_SIZE;
	dest_data = (uint32_t *)dest + OP_HISTORY_T_SIZE;
	memcpy(dest_data, src_data, src->num_records * sizeof(uint32_t));

	/* copy line lookup entries */
	src_data = (uint32_t *)src + OP_HISTORY_T_SIZE + src->max_records;
	dest_data = (uint32_t *)dest + OP_HISTORY_T_SIZE + dest->max_records;
	memcpy(dest_data, src_data, src->num_line_to_record * sizeof(uint32_t));

	/* copy byte lookup entries */
	src_data = (uint32_t *)src + OP_HISTORY_T_SIZE + src->max_records + src->max_line_to_record;
	dest_data = (uint32_t *)dest + OP_HISTORY_T_SIZE + dest->max_records + dest->max_line_to_record;;
	memcpy(dest_data, src_data, src->num_byte_to_line * sizeof(uint32_t));

	dest->frame_number = src->frame_number;
	printf("copy_op_history: resized to minimum size\n");
	print_op_history(dest);
	return dest;
}

void print_op_history(op_history_t *buf) {
	printf("op_history: frame=%d allocated=%d, records:%d of %d, lookup: %d of %d\n", buf->frame_number, buf->malloc_size, buf->num_records, buf->max_records, buf->num_line_to_record, buf->max_line_to_record);
}


// Add entry into instruction lookup table, to be called immediately before
// creating a type 10 record. Consecutive entries in the lookup table point to
// type 10 records which denote the beginning of a set of instruction deltas,
// each set of which corresponds to a single opcode and its effects. This
// lookup table is used by the front-end to display the opcodes to the user.
static inline void start_new_line(op_history_t *buf) {
	uint32_t *lookup;

	lookup = (uint32_t *)buf + OP_HISTORY_T_SIZE + buf->max_records + buf->num_line_to_record;
	buf->num_line_to_record++;
	*lookup = buf->num_records;
}

op_record_t *get_record_from_line_number(op_history_t *buf, int line_number) {
	op_record_t *op;
	uint32_t *lookup;

	// op_num = lookup[line_number]
	if (line_number >= buf->max_line_to_record) return NULL;
	lookup = (uint32_t *)buf + OP_HISTORY_T_SIZE + buf->max_records;
	op = (op_record_t *)buf + OP_HISTORY_T_SIZE + lookup[line_number];
	return op;
}

// Get pointer to next available op_record_t entry in op_history_t
static inline op_record_t *next_record(op_history_t *buf) {
	op_record_t *op;

	op = (op_record_t *)buf + OP_HISTORY_T_SIZE + buf->num_records;
	buf->num_records++;
	return op;
}

void op_history_start_frame(op_history_t *buf, uint16_t PC, int frame_number) {
	op_record_t *op;

	buf->frame_number = frame_number;
	start_new_line(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->num = 0;
	op->payload.word = PC;
	op = next_record(buf);
	op->type = 0x28;
	op->num = frame_number >> 16;
	op->payload.word = frame_number & 0xffff;
}

void op_history_end_frame(op_history_t *buf, uint16_t PC) {
	op_record_t *op;

	start_new_line(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->num = 0;
	op->payload.word = PC;
	op = next_record(buf);
	op->type = 0x29;
	op->num = 0;
	op->payload.word = 0;
}

void op_history_add_instruction(op_history_t *buf, uint16_t PC, uint8_t *opcodes, uint8_t count) {
	op_record_t *op;

	start_new_line(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->num = count;
	op->payload.word = PC;

	while (count > 0) {
		op = next_record(buf);
		op->type = *opcodes++;
		count--;
		if (count > 0) {
			op->num = *opcodes++;
			count--;
		}
		else {
			op->num = 0;
		}
		if (count > 0) {
			op->payload.byte[0] = *opcodes++;
			count--;
		}
		else {
			op->payload.byte[0] = 0;
		}
		if (count > 0) {
			op->payload.byte[1] = *opcodes++;
			count--;
		}
		else {
			op->payload.byte[1] = 0;
		}
	}
}

void op_history_one_byte_reg(op_history_t *buf, uint8_t reg, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x01;
	op->num = reg;
	op->payload.byte[0] = value;
	op->payload.byte[1] = 0;
}

void op_history_two_byte_reg(op_history_t *buf, uint8_t reg, uint16_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x02;
	op->num = reg;
	op->payload.word = value;
}

void op_history_read_address(op_history_t *buf, uint16_t addr, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x03;
	op->num = value;
	op->payload.word = addr;
}

void op_history_write_address(op_history_t *buf, uint16_t addr, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x04;
	op->num = value;
	op->payload.word = addr;
}

void op_history_computed_address(op_history_t *buf, uint16_t addr) {
	op_record_t *op = next_record(buf);

	op->type = 0x05;
	op->num = 0;
	op->payload.word = addr;
}

void op_history_new_pc(op_history_t *buf, uint16_t PC) {
	op_record_t *op = next_record(buf);

	op->type = 0x06;
	op->num = 0;
	op->payload.word = PC;
}

void op_history_branch_taken(op_history_t *buf) {
	op_record_t *op = next_record(buf);

	op->type = 0x07;
	op->num = 1;
	op->payload.word = 0;
}

void op_history_branch_not_taken(op_history_t *buf) {
	op_record_t *op = next_record(buf);

	op->type = 0x07;
	op->num = 0;
	op->payload.word = 0;
}

void op_history_opcode_ref_addr(op_history_t *buf, uint16_t addr) {
	op_record_t *op = next_record(buf);

	op->type = 0x30;
	op->num = 0;
	op->payload.word = addr;
}

// process a single operation in the history, starting at the specified
// op_record entry and continuing until the next Type 10 record or the frame
// ends. Returns -1 on error
int eval_operation(current_state_t *current, op_record_t *op) {
	int count, reg, addr;

	if (op->type != 0x10) {
#ifdef DEBUG_EVAL
		printf("found %02x as op->type when expecting 0x10!\n", op->type);
#endif
		return -1;
	}
	current->pc = op->payload.word;
	current->instruction_length = op->num;
	current->flag = 0;
	current->current_disassembler_type = current->nominal_disassembler_type;
#ifdef DEBUG_EVAL
	printf("found PC:%04x %d\n", current->pc, current->instruction_length);
#endif
	count = 0;
	while (count < current->instruction_length) {
		op++;
		current->instruction[count++] = op->type;
		current->instruction[count++] = op->num;
		current->instruction[count++] = op->payload.byte[0];
		current->instruction[count++] = op->payload.byte[1];
	}
	op++;
	while (op->type != 0x10) {
		switch (op->type) {
			case 0x01:
			reg = op->num;
			current->register_used = reg;
			current->reg_byte[reg] = op->payload.byte[0];
#ifdef DEBUG_EVAL
			printf("storing %02x in reg %d\n", op->payload.byte[0], reg);
#endif
			current->flag |= CURRENT_STATE_BYTE_REGISTER;
			break;

			case 0x02:
			reg = op->num;
			current->register_used = reg;
			current->reg_word[op->num] = op->payload.word;
			current->flag |= CURRENT_STATE_WORD_REGISTER;
			break;

			case 0x03:
			current->computed_addr = op->payload.word;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR | CURRENT_STATE_MEMORY_READ;
			break;

			case 0x04:
			addr = op->payload.word;
			current->computed_addr = addr;
			current->memory[addr] = op->num;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR | CURRENT_STATE_MEMORY_WRITE;
			break;

			case 0x05:
			current->opcode_ref_addr = op->payload.word;
			current->flag |= CURRENT_STATE_OPCODE_ADDR;
			break;

			case 0x06:
			current->pc = op->payload.word;
			current->flag |= CURRENT_STATE_JMP;
			break;

			case 0x07:
			if (op->num) {
				current->flag |= CURRENT_STATE_BRANCH_TAKEN;
			}
			current->flag |= CURRENT_STATE_BRANCH;
			break;

			case 0x30:
			current->computed_addr = op->payload.word;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR;
			break;

			case 0x28: // start of frame
			current->flag = CURRENT_STATE_OTHER_DISASSEMBLER_TYPE;
			current->current_disassembler_type = op->type;
			goto done;

			case 0x29: // end of frame
			current->flag = CURRENT_STATE_OTHER_DISASSEMBLER_TYPE;
			current->current_disassembler_type = op->type;
			goto done;

			case 0x2e: // start of NMI
			current->flag = CURRENT_STATE_OTHER_DISASSEMBLER_TYPE;
			current->current_disassembler_type = op->type;
			goto done;

			case 0x2f: // end of NMI
			current->flag = CURRENT_STATE_OTHER_DISASSEMBLER_TYPE;
			current->current_disassembler_type = op->type;
			goto done;
		}
#ifdef DEBUG_EVAL
		printf("  found op type %02x", op->type);
		if (current->flag & CURRENT_STATE_BYTE_REGISTER) {
			printf(", byte reg %d=%x", current->register_used, current->reg_byte[current->register_used]);
		}
		if (current->flag & CURRENT_STATE_WORD_REGISTER) {
			printf(", word reg %d=%x", current->register_used, current->reg_word[current->register_used]);
		}
		if (current->flag & CURRENT_STATE_COMPUTED_ADDR) {
			printf(", computed addr=%04x", current->computed_addr);
		}
		if (current->flag & CURRENT_STATE_OPCODE_ADDR) {
			printf(", opcode addr=%04x", current->opcode_ref_addr);
		}
		if (current->flag & CURRENT_STATE_BRANCH) {
			printf(", branch");
			if (current->flag & CURRENT_STATE_BRANCH_TAKEN) {
				printf(" taken");
			}
			else {
				printf(" not taken");
			}
		}
		if (current->flag & CURRENT_STATE_JMP) {
			printf(", new pc=%04x", current->pc);
		}
		printf("\n");
#endif
		op++;
	}
done:
#ifdef DEBUG_EVAL
	printf("  finished; last op type: %02x\n", op->type);
#endif
	return op->type;
}
