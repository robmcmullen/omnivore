#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"

/*#define DEBUG_STACK */
#define DEBUG_BREAKPOINT 

int access_color_step = 5;


void libdebugger_init_array(breakpoints_t *breakpoints) {
	memset(breakpoints, 0, sizeof(breakpoints_t));
}

typedef struct {
	uint16_t stack[TOKENS_PER_BREAKPOINT];
	int index;
	int error;
} stack_t;

void clear(stack_t *s) {
	s->index = 0;
	s->error = 0;
}

void push(stack_t *s, uint16_t value) {
	if (s->index >= TOKENS_PER_BREAKPOINT) {
		s->error = STACK_OVERFLOW;
	}
	else {
		s->stack[s->index++] = value;
	}
#ifdef DEBUG_STACK
	printf("push; (err=%d) stack is now: ", s->error);
	for (int i=0; i<s->index; i++) {
		printf("%x,", s->stack[i]);
	}
	printf("\n");
#endif
}

uint16_t pop(stack_t *s) {
	uint16_t value;

	if (s->index > 0) {
		value = (uint16_t)(s->stack[--s->index]);
	}
	else {
		s->error = STACK_UNDERFLOW;
		value = 0;
	}
#ifdef DEBUG_STACK
	printf("pop; (err=%d) stack is now: ", s->error);
	for (int i=0; i<s->index; i++) {
		printf("%x,", s->stack[i]);
	}
	printf("\n");
#endif
	return value;
}

void process_binary(uint16_t token, stack_t *s) {
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
#ifdef DEBUG_STACK
		printf("process_binary: op=%d first=%d second=%d value=%d\n", token, first, second, value);
#endif
		push(s, value);
	}
}

int process_unary(uint16_t token, cpu_state_callback_ptr get_emulator_value, stack_t *s) {
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_check_breakpoints(breakpoints_t *breakpoints, int cycles, cpu_state_callback_ptr get_emulator_value) {
	uint16_t token, addr, value;
	int i, num_entries, index, status, final_value, count;
	stack_t stack;

	num_entries = breakpoints->num_breakpoints;

	for (i=0; i < num_entries; i++) {
		status = breakpoints->breakpoint_status[i];
		if (status & BREAKPOINT_ENABLED) {
#ifdef DEBUG_BREAKPOINT
			printf("Breakpoint %d enabled\n", i);
#endif

			index = i * TOKENS_PER_BREAKPOINT;
			if (i == 0) { /* Check the zeroth breakpoint for step conditions */
				count = (int)breakpoints->tokens[index]; /* tokens are unsigned */
				if (status == BREAKPOINT_COUNT_CYCLES) {
					if (count - cycles <= 0) return 0;
					else breakpoints->tokens[index] -= cycles;
					continue;
				}
				else if (status == BREAKPOINT_COUNT_INSTRUCTIONS) {
					if (--count <= 0) return 0;
					else breakpoints->tokens[index] -= 1;
					continue;
				}
				/* otherwise, process normally */
			}
			clear(&stack);
			for (count=0; count < TOKENS_PER_BREAKPOINT - 1; count++) {
				token = breakpoints->tokens[index++];
#ifdef DEBUG_BREAKPOINT
				printf("index=%d, count=%d token=%x\n", index-1, count, token);
#endif
				if (token == END_OF_LIST) goto compute;

				if (token & OP_BINARY) {
#ifdef DEBUG_BREAKPOINT
					printf("binary: op=%d\n", token & TOKEN_FLAG);
#endif
					process_binary(token, &stack);
				}
				else if (token & OP_UNARY) {
#ifdef DEBUG_BREAKPOINT
					printf("unary: op=%d\n", token & TOKEN_FLAG);
#endif
					process_unary(token, get_emulator_value, &stack);
				}
				else {
					if (token & VALUE_ARGUMENT) {
						addr = breakpoints->tokens[index++];
					}
					else {
						addr = 0;
					}
					if ((token & TOKEN_FLAG) == NUMBER) {
						value = addr;
#ifdef DEBUG_BREAKPOINT
						printf("number: op=%d value=%04x\n", token & TOKEN_FLAG, addr);
#endif

					}
					else {
						value = get_emulator_value(token, addr);
#ifdef DEBUG_BREAKPOINT
						printf("emu value: op=%d value=%04x\n", token & TOKEN_FLAG, value);
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

#define ACCESS_COLOR_NORMAL_MAX 128
#define ACCESS_COLOR_NORMAL_MIN 32

/* Reduce brightness of each access at start of each frame */
void libdebugger_memory_access_start_frame(frame_status_t *output) {
	uint8_t val, *ptr;

	for (ptr=output->memory_access; ptr<&output->memory_access[MAIN_MEMORY_SIZE]; ptr++) {
		val = *ptr;
		if (val > ACCESS_COLOR_NORMAL_MAX) *ptr = ACCESS_COLOR_NORMAL_MAX;
		else if (val > ACCESS_COLOR_NORMAL_MIN) *ptr = val - access_color_step;
		else *ptr = ACCESS_COLOR_NORMAL_MIN;
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

int libdebugger_calc_frame(emu_frame_callback_ptr calc, frame_status_t *output, breakpoints_t *breakpoints) {
	int bpid;

	switch (output->frame_status) {
		case FRAME_BREAKPOINT:
		output->breakpoint_id = 0;
		libdebugger_memory_access_finish_frame(output);
		break;

		default:
		output->frame_number += 1;
		output->current_instruction_in_frame = 0;
		output->current_cycle_in_frame = 0;
		libdebugger_memory_access_start_frame(output);
	}
	output->frame_status = FRAME_INCOMPLETE;
	bpid = calc(output, breakpoints);
	if (bpid < 0) {
		output->frame_status = FRAME_FINISHED;
		// libdebugger_memory_access_finish_frame(output);
	}
	return bpid;
}
