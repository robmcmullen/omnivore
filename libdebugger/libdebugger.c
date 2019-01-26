#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"


int access_color_step = 5;


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

int process_unary(uint16_t token, cpu_state_callback_ptr get_emulator_value, postfix_stack_t *s) {
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_brk_instruction(breakpoints_t *breakpoints) {
	breakpoints->breakpoint_status[0] = BREAKPOINT_ENABLED;
	breakpoints->breakpoint_type[0] = BREAKPOINT_BRK_INSTRUCTION;
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_check_breakpoints(breakpoints_t *breakpoints, frame_status_t *run, cpu_state_callback_ptr get_emulator_value, int is_unconditional_jmp) {
	uint16_t token, op, addr, value;
	int64_t ref_val;
	int i, num_entries, index, status, btype, final_value, count, current_pc;
	postfix_stack_t stack;

	current_pc = get_emulator_value(REG_PC, 0);
	// printf("in libdebugger_check_breakpoints: PC=%04x breakpoint->last_pc=%04x\n", current_pc, breakpoints->last_pc);
	if ((breakpoints->last_pc == current_pc) && is_unconditional_jmp) {
		/* found infinite loop when same instruction calls itself */
		breakpoints->breakpoint_status[0] = BREAKPOINT_ENABLED;
		breakpoints->breakpoint_type[0] = BREAKPOINT_INFINITE_LOOP;
		return 0;
	}

	num_entries = breakpoints->num_breakpoints;

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
		else if (btype == BREAKPOINT_COUNT_FRAMES) {
			/* only checked at the end of the frame */
			;
		}
	}

	/* process normal breakpoints */
	for (i=1; i < num_entries; i++) {
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
					process_unary(token, get_emulator_value, &stack);
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
	return -1;
}

#define ACCESS_COLOR_NORMAL_MAX 192
#define ACCESS_COLOR_NORMAL_MIN 64

/* Reduce brightness of each access at start of each frame */
void libdebugger_memory_access_start_frame(uint8_t *memory, frame_status_t *output) {
	uint8_t val, *ptr, *a, *mem;

	for (ptr=output->memory_access, a=output->access_type, mem=memory; ptr<&output->memory_access[MAIN_MEMORY_SIZE]; ptr++, a++, mem++) {
		val = *ptr;
		if (val > ACCESS_COLOR_NORMAL_MAX) *ptr = ACCESS_COLOR_NORMAL_MAX;
		else {
			if (val > ACCESS_COLOR_NORMAL_MIN) {
				*ptr = val - access_color_step;
				*a = *a & 0x0f;
			}
			else {
				*ptr = *mem >> 2;
				*a = 0;
			}
		}
	}
}

/* Reduce brightness of most recent access at end of frame, but not called if
	the	frame doesn't reach the end due to a breakpoint. This allows the
	location of the current access to be shown as value 255 when single
	stepping.
*/
void libdebugger_memory_access_finish_frame(frame_status_t *output) {
	uint8_t val, *ptr;

	for (ptr=output->memory_access; ptr<&output->memory_access[MAIN_MEMORY_SIZE]; ptr++) {
		val = *ptr;
		if (val > ACCESS_COLOR_NORMAL_MAX) *ptr = ACCESS_COLOR_NORMAL_MAX;
	}
}

int libdebugger_calc_frame(emu_frame_callback_ptr calc, uint8_t *memory, frame_status_t *output, breakpoints_t *breakpoints, emulator_history_t *history) {
	int bpid, ref_val;
	history_frame_t *frame_entry;

	switch (output->frame_status) {
		case FRAME_BREAKPOINT:
		output->breakpoint_id = 0;
		libdebugger_memory_access_finish_frame(output);
		break;

		default:
		output->frame_number += 1;
		output->current_instruction_in_frame = 0;
		output->current_cycle_in_frame = 0;
		libdebugger_memory_access_start_frame(memory, output);
	}
	output->frame_status = FRAME_INCOMPLETE;
	bpid = calc(output, breakpoints, history);
	if (bpid < 0) {
		int status, index, count;

		output->frame_status = FRAME_FINISHED;
		// libdebugger_memory_access_finish_frame(output);

		frame_entry = (history_frame_t *)libudis_get_next_entry(history, DISASM_FRAME_END);
		if (frame_entry) {
			frame_entry->frame_number = output->frame_number;
		}

		/* special check for frame count breakpoint */
		status = breakpoints->breakpoint_status[0];
		if (breakpoints->breakpoint_status[0] == BREAKPOINT_ENABLED && breakpoints->breakpoint_type[0] == BREAKPOINT_COUNT_FRAMES) {
			index = 0;
			count = (int)breakpoints->tokens[index]; /* tokens are unsigned */
			ref_val = breakpoints->reference_value[index];
#ifdef DEBUG_BREAKPOINT
			printf("checking breakpoint 0 for frame number: current frame number=%d, count=%d, ref=%ld\n", output->frame_number, count, ref_val);
#endif
			if (count + ref_val <= output->frame_number) bpid = 0;
		}
	}
	if (bpid == 0) {
		/* breakpoint 0 is always used to store one-time breakpoints, so they
		 must be marked as disabled to not fire next time. */
		breakpoints->breakpoint_status[0] = BREAKPOINT_DISABLED;
	}
	return bpid;
}
