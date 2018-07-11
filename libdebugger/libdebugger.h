#include <stdint.h>

/* The debugger structure must match the definition in omni8bit/debugger/dtypes.py */

#define NUM_BREAKPOINT_ENTRIES 256
#define NUM_WATCHPOINT_ENTRIES 256
#define NUM_WATCHPOINT_TERMS 16384
#define MAX_TERMS_PER_WATCHPOINT 255

/* breakpoint/watchpoint status values */
#define BREAKPOINT_EMPTY 0
#define BREAKPOINT_ENABLED 1
#define BREAKPOINT_DISABLED 2
#define EVALUATION_ERROR 3
#define INDEX_OUT_OF_RANGE 4
#define TOO_MANY_TERMS 5
#define STACK_UNDERFLOW 6  /* too many operators/not enough values */
#define STACK_OVERFLOW 7  /* too many values */

/* status values returned */
#define NO_BREAKPOINT_FOUND -1

typedef struct {
        /* Change from uint8_t if number of entries is greater than 256 */
        uint8_t num_breakpoints,
        uint8_t num_watchpoints,

        uint16_t breakpoint_address[NUM_BREAKPOINT_ENTRIES],
        uint8_t breakpoint_status[NUM_BREAKPOINT_ENTRIES],

        uint16_t watchpoint_term[NUM_WATCHPOINT_TERMS],
        uint8_t watchpoint_status[NUM_WATCHPOINT_ENTRIES],
        uint8_t watchpoint_index[NUM_WATCHPOINT_ENTRIES],
        uint8_t watchpoint_length[NUM_WATCHPOINT_ENTRIES],
} debugger_t;


/* library functions defined in libdebugger.c */

void libdebugger_init_array(debugger_t *state);

int libdebugger_check_breakpoints(debugger_t *state, uint16_t pc);

typedef uint16_t (*cpu_state_callback_ptr)(uint16_t term, uint16_t addr);

int libdebugger_check_watchpoints(debugger_t *state, cpu_state_callback_ptr get_emulator_value);
