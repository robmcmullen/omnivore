#include <stdint.h>

#include "6502.h"


/* variables internal to 6502.c that we need to see */

extern int lengths[];

extern Instruction inst;

extern int jumping;

/* new stuff for lib6502 */

typedef struct {
        uint32_t frame_number;
        uint64_t total_cycles;
        uint16_t PC;
        uint8_t A;
        uint8_t X;
        uint8_t Y;
        uint8_t SP;
        uint8_t SR;
        uint8_t breakpoint_hit;
        uint8_t memory[1<<16];
} ProcessorState;

extern long cycles_per_frame;

/* library functions defined in lib6502.c */

void lib6502_init_cpu(float frequency_mhz, float refresh_rate_hz);

void lib6502_get_current_state(ProcessorState *buf);

void lib6502_restore_state(ProcessorState *buf);

int lib6502_step_cpu();

long lib6502_next_frame();
