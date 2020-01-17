#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"

int access_color_step = 5;

emulator_state_t *create_emulator_state(int save_size, int input_size, int video_size, int audio_size) {
	emulator_state_t *buf;
	int total_size;

	total_size = sizeof(emulator_state_t) + save_size + input_size + video_size + audio_size;
	buf = (emulator_state_t *)malloc(total_size);
	buf->malloc_size = total_size;
    buf->magic = LIBDEBUGGER_SAVE_STATE_MAGIC;
    buf->frame_number = -1;
    buf->emulator_id = -1;
    buf->input_offset = sizeof(emulator_state_t);
    buf->input_size = input_size;
    buf->save_state_offset = buf->input_offset + input_size;
    buf->save_state_size = save_size;
    buf->video_offset = buf->save_state_offset + save_size;
    buf->video_size = video_size;
    buf->audio_offset = buf->video_offset + video_size;
    buf->audio_size = audio_size;

    return buf;
}


/* instruction history utility functions */

op_history_t *create_op_history(int max_records, int max_lookup) {
	op_history_t *buf;
	int num;
	int total_size;

	num = OP_HISTORY_T_SIZE + max_records + max_lookup;
	total_size = num * 4; // 4 bytes per uint32
	buf = (op_history_t *)malloc(total_size);
	buf->malloc_size = total_size;
	buf->max_records = max_records;
	buf->max_lookup = max_lookup;
	buf->frame_number = 0;
	clear_op_history(buf);
	return buf;
}

void clear_op_history(op_history_t *buf) {
	buf->num_records = 0;
	buf->num_lookup = 0;
}

op_history_t *copy_op_history(op_history_t *src) {
	op_history_t *dest;
	uint32_t *src_data;
	uint32_t *dest_data;

	dest = create_op_history(src->num_records, src->num_lookup);
	dest->num_records = dest->max_records;
	dest->num_lookup = dest->max_lookup;

	/* copy delta entries */
	src_data = (uint32_t *)src + OP_HISTORY_T_SIZE;
	dest_data = (uint32_t *)dest + OP_HISTORY_T_SIZE;
	memcpy(dest_data, src_data, src->num_records * sizeof(uint32_t));

	/* copy lookup entries */
	src_data = (uint32_t *)src + OP_HISTORY_T_SIZE + src->max_records;
	dest_data = (uint32_t *)dest + OP_HISTORY_T_SIZE + dest->max_records;
	memcpy(dest_data, src_data, src->num_lookup * sizeof(uint32_t));

	dest->frame_number = src->frame_number;
	printf("copy_op_history: resized to minimum size\n");
	print_op_history(dest);
	return dest;
}

void print_op_history(op_history_t *buf) {
	printf("op_history: frame=%d allocated=%d, records:%d of %d, lookup: %d of %d\n", buf->frame_number, buf->malloc_size, buf->num_records, buf->max_records, buf->num_lookup, buf->max_lookup);
}


// Add entry into instruction lookup table, to be called immediately before
// creating a type 10 record. Consecutive entries in the lookup table point to
// type 10 records which denote the beginning of a set of instruction deltas,
// each set of which corresponds to a single opcode and its effects. This
// lookup table is used by the front-end to display the opcodes to the user.
static inline void add_new_op_lookup(op_history_t *buf) {
	uint32_t *lookup;

	lookup = (uint32_t *)buf + OP_HISTORY_T_SIZE + buf->max_records + buf->num_lookup;
	buf->num_lookup++;
	*lookup = buf->num_records;
}

op_record_t *get_record_from_line_number(op_history_t *buf, int line_number) {
	op_record_t *op;
	uint32_t *lookup;

	// op_num = lookup[line_number]
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
	add_new_op_lookup(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->payload1 = PC & 0xff;
	op->payload2 = PC >> 8;
	op->payload3 = 0;
	op = next_record(buf);
	op->type = 0x28;
	op->payload1 = frame_number & 0xff;
	op->payload2 = (frame_number >> 8) & 0xff;
	op->payload3 = frame_number >> 16;
}

void op_history_end_frame(op_history_t *buf, uint16_t PC) {
	op_record_t *op;

	add_new_op_lookup(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->payload1 = PC & 0xff;
	op->payload2 = PC >> 8;
	op->payload3 = 0;
	op = next_record(buf);
	op->type = 0x29;
	op->payload1 = 0;
	op->payload2 = 0;
	op->payload3 = 0;
}

void op_history_add_instruction(op_history_t *buf, uint16_t PC, uint8_t *opcodes, uint8_t count) {
	op_record_t *op;

	add_new_op_lookup(buf);
	op = next_record(buf);
	op->type = 0x10;
	op->payload1 = PC & 0xff;
	op->payload2 = PC >> 8;
	op->payload3 = count;

	while (count > 0) {
		op = next_record(buf);
		op->type = *opcodes++;
		count--;
		if (count > 0) {
			op->payload1 = *opcodes++;
			count--;
		}
		else {
			op->payload1 = 0;
		}
		if (count > 0) {
			op->payload2 = *opcodes++;
			count--;
		}
		else {
			op->payload2 = 0;
		}
		if (count > 0) {
			op->payload3 = *opcodes++;
			count--;
		}
		else {
			op->payload3 = 0;
		}
	}
}

void op_history_one_byte_reg(op_history_t *buf, uint8_t reg, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x01;
	op->payload1 = reg;
	op->payload2 = value;
	op->payload3 = 0;
}

void op_history_two_byte_reg(op_history_t *buf, uint8_t reg, uint16_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x02;
	op->payload1 = reg;
	op->payload2 = value & 0xff;
	op->payload3 = value >> 8;
}

void op_history_read_address(op_history_t *buf, uint16_t addr, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x03;
	op->payload1 = addr & 0xff;
	op->payload2 = addr >> 8;
	op->payload3 = value;
}

void op_history_write_address(op_history_t *buf, uint16_t addr, uint8_t value) {
	op_record_t *op = next_record(buf);

	op->type = 0x04;
	op->payload1 = addr & 0xff;
	op->payload2 = addr >> 8;
	op->payload3 = value;
}

void op_history_computed_address(op_history_t *buf, uint16_t addr) {
	op_record_t *op = next_record(buf);

	op->type = 0x05;
	op->payload1 = addr & 0xff;
	op->payload2 = addr >> 8;
	op->payload3 = 0;
}

void op_history_new_pc(op_history_t *buf, uint16_t PC) {
	op_record_t *op = next_record(buf);

	op->type = 0x06;
	op->payload1 = PC & 0xff;
	op->payload2 = PC >> 8;
	op->payload3 = 0;
}

void op_history_branch_taken(op_history_t *buf) {
	op_record_t *op = next_record(buf);

	op->type = 0x07;
	op->payload1 = 1;
	op->payload2 = 0;
	op->payload3 = 0;
}

void op_history_branch_not_taken(op_history_t *buf) {
	op_record_t *op = next_record(buf);

	op->type = 0x07;
	op->payload1 = 0;
	op->payload2 = 0;
	op->payload3 = 0;
}

void op_history_opcode_ref_addr(op_history_t *buf, uint16_t addr) {
	op_record_t *op = next_record(buf);

	op->type = 0x30;
	op->payload1 = addr & 0xff;
	op->payload2 = addr >> 8;
	op->payload3 = 0;
}

// process a single operation in the history, starting at the specified
// op_history entry and continuing until the next Type 10 record or the frame
// ends. Returns -1 on error
int eval_operation(current_state_t *current, op_record_t *op) {
	int count, reg, addr;

	if (op->type != 0x10) {
		return -1;
	}
	current->pc = op->payload1 + (op->payload2 << 8);
	current->instruction_length = op->payload3;
	current->flag = 0;
	printf("found PC:%04x %d\n", current->pc, current->instruction_length);
	count = 0;
	while (count < current->instruction_length) {
		op++;
		current->instruction[count++] = op->type;
		current->instruction[count++] = op->payload1;
		current->instruction[count++] = op->payload2;
		current->instruction[count++] = op->payload3;
	}
	op++;
	while (op->type != 0x10) {
		switch (op->type) {
			case 0x01:
			reg = op->payload1;
			current->register_used = reg;
			current->reg_byte[reg] = op->payload2;
			printf("storing %02x in reg %d\n", op->payload2, reg);
			current->flag |= CURRENT_STATE_BYTE_REGISTER;
			break;

			case 0x02:
			reg = op->payload1;
			current->register_used = reg;
			current->reg_word[op->payload1] = op->payload2 + (op->payload3 << 8);
			current->flag |= CURRENT_STATE_WORD_REGISTER;
			break;

			case 0x03:
			addr = op->payload1 + (op->payload2 << 8);
			current->computed_addr = addr;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR | CURRENT_STATE_MEMORY_READ;
			break;

			case 0x04:
			addr = op->payload1 + (op->payload2 << 8);
			current->computed_addr = addr;
			current->memory[addr] = op->payload3;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR | CURRENT_STATE_MEMORY_WRITE;
			break;

			case 0x05:
			addr = op->payload1 + (op->payload2 << 8);
			current->opcode_ref_addr = addr;
			current->flag |= CURRENT_STATE_OPCODE_ADDR;
			break;

			case 0x06:
			addr = op->payload1 + (op->payload2 << 8);
			current->pc = addr;
			current->flag |= CURRENT_STATE_JMP;
			break;

			case 0x07:
			if (op->payload1) {
				current->flag |= CURRENT_STATE_BRANCH_TAKEN;
			}
			current->flag |= CURRENT_STATE_BRANCH;
			break;

			case 0x30:
			addr = op->payload1 + (op->payload2 << 8);
			current->computed_addr = addr;
			current->flag |= CURRENT_STATE_COMPUTED_ADDR;
			break;

			case 0x29:
			// end of frame
			goto done;
		}
		printf("  found op type %02x:", op->type);
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
		op++;
	}
done:
	return 0;
}


void libdebugger_init_array(breakpoints_t *breakpoints) {
	memset(breakpoints, 0, sizeof(breakpoints_t));
	breakpoints->last_pc = -1;
}

typedef struct {
	uint16_t stack[TOKENS_PER_BREAKPOINT];
	int index;
	int error;
} postfix_stack_t;

void clear(postfix_stack_t *s) {
	s->index = 0;
	s->error = 0;
}

void push(postfix_stack_t *s, uint16_t value) {
	if (s->index >= TOKENS_PER_BREAKPOINT) {
		s->error = STACK_OVERFLOW;
	}
	else {
		s->stack[s->index++] = value;
	}
#ifdef DEBUG_POSTFIX_STACK
	printf("push; (err=%d) stack is now: ", s->error);
	for (int i=0; i<s->index; i++) {
		printf("%x,", s->stack[i]);
	}
	printf("\n");
#endif
}

uint16_t pop(postfix_stack_t *s) {
	uint16_t value;

	if (s->index > 0) {
		value = (uint16_t)(s->stack[--s->index]);
	}
	else {
		s->error = STACK_UNDERFLOW;
		value = 0;
	}
#ifdef DEBUG_POSTFIX_STACK
	printf("pop; (err=%d) stack is now: ", s->error);
	for (int i=0; i<s->index; i++) {
		printf("%x,", s->stack[i]);
	}
	printf("\n");
#endif
	return value;
}

void process_binary(uint16_t token, postfix_stack_t *s) {
	uint16_t first, second, value;

	first = pop(s);
	second = pop(s);
	value = 0;
	if (!s->error) {
		switch(token) {
			case OP_PLUS:
			value = first + second;
			break;

			case OP_MINUS:
			value = first - second;
			break;

			case OP_EQ:
			value = first == second;
			break;

			case OP_LOGICAL_AND:
			value = first && second;
			break;

			default:
			printf("unimplemented binary operation: token=%d\n", token);
			break;
		}
#ifdef DEBUG_POSTFIX_STACK
		printf("process_binary: op=%d first=%d second=%d value=%d\n", token, first, second, value);
#endif
		push(s, value);
	}
}

int process_unary(uint16_t token, postfix_stack_t *s) {
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_brk_instruction(breakpoints_t *breakpoints) {
	breakpoints->breakpoint_status[0] = BREAKPOINT_ENABLED;
	breakpoints->breakpoint_type[0] = BREAKPOINT_BRK_INSTRUCTION;
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_check_breakpoints(breakpoints_t *breakpoints, op_history_t *history, int start_index) {
#ifdef NOT_USING_DEBUGGER_YET
	uint16_t token, op, addr, value;
	int64_t ref_val;
	int i, num_entries, index, status, btype, final_value, count, current_pc, current_scan_line, start_checking_breakpoints_at;
	postfix_stack_t stack;

	current_pc = get_emulator_value(REG_PC, 0);
	// printf("in libdebugger_check_breakpoints: PC=%04x breakpoint->last_pc=%04x\n", current_pc, breakpoints->last_pc);
#ifdef DEBUG_DETECT_INFINTE_LOOP
	/* infinite loop detection when same instruction calls itself. This is only
	useful if the machine has no interrupts, because during an interrupt, self-
	modifying code could be used to defeat this detection.
	*/
	if ((breakpoints->last_pc == current_pc) && is_unconditional_jmp) {
		breakpoints->breakpoint_status[0] = BREAKPOINT_ENABLED;
		breakpoints->breakpoint_type[0] = BREAKPOINT_INFINITE_LOOP;
		return 0;
	}
#endif

	current_scan_line = get_emulator_value(EMU_SCANLINE, 0);
	if (current_scan_line != run->current_scan_line_in_frame) {
		run->current_scan_line_in_frame = current_scan_line;
		run->scan_lines_since_power_on++;
	}

	num_entries = breakpoints->num_breakpoints;
	start_checking_breakpoints_at = 1;

	/* Special case for zeroth breakpoint: step conditions & user control */
	if (breakpoints->breakpoint_status[0] == BREAKPOINT_ENABLED) {
		btype = breakpoints->breakpoint_type[0];
		count = (int)breakpoints->tokens[0]; /* tokens are unsigned */
		ref_val = breakpoints->reference_value[0];
#ifdef DEBUG_BREAKPOINT
		printf("checking breakpoint 0: %d, count=%d, ref=%ld\n", btype, count, ref_val);
#endif
		if (btype == BREAKPOINT_COUNT_CYCLES) {
			if (count + ref_val <= run->cycles_since_power_on) return 0;
		}
		else if (btype == BREAKPOINT_COUNT_INSTRUCTIONS) {
			if (count + ref_val <= run->instructions_since_power_on) return 0;
		}
		else if (btype == BREAKPOINT_COUNT_LINES) {
			if (count + ref_val <= run->scan_lines_since_power_on) return 0;
		}
		else if (btype == BREAKPOINT_COUNT_FRAMES) {
			/* only checked at the end of the frame */
			;
		}
		else if (btype == BREAKPOINT_CONDITIONAL) {
			/* use regular breakpoint rules for conditional types */
			start_checking_breakpoints_at = 0;
		}
	}

	/* process normal breakpoints */
	for (i=start_checking_breakpoints_at; i < num_entries; i++) {
		status = breakpoints->breakpoint_status[i];
		if (status == BREAKPOINT_ENABLED) {
			btype = breakpoints->breakpoint_type[i];
#ifdef DEBUG_BREAKPOINT
			printf("Breakpoint %d enabled: type=%d\n", i, btype);
#endif
			index = i * TOKENS_PER_BREAKPOINT;
			clear(&stack);
			for (count=0; count < TOKENS_PER_BREAKPOINT - 1; count++) {
				token = breakpoints->tokens[index++];
				op = token & OP_MASK;
#ifdef DEBUG_BREAKPOINT
				printf("  index=%d, count=%d token=%x\n", index-1, count, token);
#endif
				if (token == END_OF_LIST) goto compute;

				if (op == OP_BINARY) {
#ifdef DEBUG_BREAKPOINT
					printf("  binary: op=%d\n", op);
#endif
					process_binary(token, &stack);
				}
				else if (op == OP_UNARY) {
#ifdef DEBUG_BREAKPOINT
					printf("  unary: op=%d\n", op);
#endif
					process_unary(token, &stack);
				}
				else {
					if (op == VALUE_ARGUMENT) {
						addr = breakpoints->tokens[index++];
					}
					else {
						addr = 0;
					}
					if (token == NUMBER) {
						value = addr;
#ifdef DEBUG_BREAKPOINT
						printf("  number: op=%d value=%04x\n", op, addr);
#endif

					}
					else {
						value = get_emulator_value(token, addr);
#ifdef DEBUG_BREAKPOINT
						printf("  emu value: op=%d value=%04x\n", op, value);
#endif
					}
					push(&stack, value);
				}
				if (stack.error) {
					breakpoints->breakpoint_status[i] = stack.error;
					goto next;
				}
			}
compute:
			final_value = pop(&stack);
			if (stack.error) {
				breakpoints->breakpoint_status[i] = stack.error;
				goto next;
			}
			if (final_value != 0) {
				/* condition true, so the breakpoint should be triggered! */
				return i;
			}
		}
next: ;
	}
#endif /* NOT_USING_DEBUGGER_YET */
	return -1;
}
