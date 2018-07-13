#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"


void libdebugger_init_array(debugger_t *state) {
	memset(state, 0, sizeof(debugger_t));
}

typedef struct {
	int stack[TOKENS_PER_BREAKPOINT];
	int index;
	int error;
} stack_t;

void clear(stack_t *s) {
	s->index = 0;
	s->error = 0;
}

int push(stack_t *s, int value) {
	if (s->index >= TOKENS_PER_BREAKPOINT) {
		s->error = STACK_OVERFLOW;
	}
	else {
		s->stack[s->index++] = value;
	}
}

int pop(stack_t *s) {
	if (s->index > 0) {
		return (int)(s->stack[s->index--]);
	}
	s->error = STACK_UNDERFLOW;
}

int process_binary(uint16_t token, stack_t *s) {
	int first, second, value;

	first = pop(s);
	second = pop(s);
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
		}
		push(s, value);
	}
}

int process_unary(uint16_t token, cpu_state_callback_ptr get_emulator_value, stack_t *s) {
	return 0;
}

/* returns: index number of breakpoint or -1 if no breakpoint condition met. */
int libdebugger_check_breakpoints(debugger_t *state, cpu_state_callback_ptr get_emulator_value) {
	uint16_t token, addr, value;
	int i, num_entries, index, status, final_value, count;
	stack_t stack;

	num_entries = state->num_breakpoints;

	for (i=0; i < num_entries; i++) {
		if (state->breakpoint_status[i] == BREAKPOINT_ENABLED) {
			index = i * TOKENS_PER_BREAKPOINT;
			clear(&stack);
			for (count=0; count < TOKENS_PER_BREAKPOINT - 1; count++) {
				token = state->tokens[index++];
				if (token == END_OF_LIST) goto compute;

				if (token & OP_BINARY) {
					process_binary(token, &stack);
				}
				else if (token & OP_UNARY) {
					process_unary(token, get_emulator_value, &stack);
				}
				else {
					if (token & VALUE_ARGUMENT) {
						addr = state->tokens[index++];
					}
					else {
						addr = 0;
					}
					if (token == NUMBER) {
						value = addr;
					}
					else {
						value = get_emulator_value(token, addr);
					}
					push(&stack, value);
				}
				if (stack.error) {
					state->breakpoint_status[i] = stack.error;
					goto next;
				}
			}
compute:
			final_value = pop(&stack);
			if (stack.error) {
				state->breakpoint_status[i] = stack.error;
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
