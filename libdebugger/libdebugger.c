#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"


void libdebugger_init_array(debugger_t *state) {
	memset(state, 0, sizeof(debugger_t));
}

/* returns: index number of breakpoint if found or -1 if no breakpoint found */
int libdebugger_check_breakpoints(debugger_t *state, uint16_t pc) {
	int i, num_entries;

	num_entries = state->num_breakpoints;

	for (i=0; i < num_entries; i++) {
		if (state->breakpoint_status == BREAKPOINT_ENABLED) {
			if (pc == state->breakpoint_address[i]) {
				return i;
			}
		}
	}
	return -1;
}

typedef struct {
	uint16_t stack[MAX_TERMS_PER_WATCHPOINT];
	int index;
} stack_t;

int push(stack *s, uint16_t value) {
	if (s->index >= MAX_TERMS_PER_WATCHPOINT) {
		return -STACK_OVERFLOW;
	}
	s->stack[s->index++] = value;
	return 0;
}

int pop(stack *s) {
	if (s->index > 0) {
		return (int)(s->stack[s->stack_index--]);
	}
	return -STACK_UNDERFLOW;
}

int process_binary(uint16_t cmd, stack *s) {
	return 0;
}

int process_unary(uint16_t cmd, stack *s) {
	return 0;
}

/* returns: index number of watchpoint if found or -1 if no breakpoint found */
int libdebugger_check_watchpoints(debugger_t *state, cpu_state_callback_ptr get_emulator_value) {
	uint16_t cmd, addr, value;
	int i, num_entries, index;
	stack_t stack;

	num_entries = state->num_watchpoints;

	for (i=0; i < num_entries; i++) {
		if (state->watchpoint_status[i] == BREAKPOINT_ENABLED) {
			index = state->watchpoint_index[i];
			count = state->watchpoint_length[i];
			if (count > MAX_TERMS_PER_WATCHPOINT) {
				state->watchpoint_status[i] = TOO_MANY_TERMS;
				goto next;
			}
			stack.index = 0;
			while (count > 0) {
				count -= 1;
				if (index >= NUM_WATCHPOINT_TERMS - 1) {
					state->watchpoint_status[i] = INDEX_OUT_OF_RANGE;
					goto next;
				}
				cmd = state->watchpoint_term[index++];
				addr = state->watchpoint_term[index++];

				if (cmd & OP_BINARY) {
					status = process_binary(cmd, &stack);
				}
				else if (cmd & OP_UNARY) {
					status = process_unary(cmd, &stack);
				}
				else {
					value = get_emulator_value(cmd, addr);
					status = push(&stack, value);
				}
				if (status < 0) {
					state->watchpoint_status[i] = -status;
					goto next;
				}
			}
			final_value = pop(&stack);
			if (final_value < 0) {
				state->watchpoint_status[i] = -status;
				goto next;
			}
			if (final_value != 0) {
				/* watchpoint should be triggered! */
				return i;
			}
		}
next:
	}
	return -1;
}
