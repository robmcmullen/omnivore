#include <stdint.h>

#include "6502.h"
#include "libdebugger.h"


/* variables internal to 6502.c that we need to see */

extern int lengths[];

extern Instruction inst;

extern int jumping;

/* macros to save variables to (possibly unaligned) data buffer */

#define save16(buf, var) memcpy(buf, &var, 2)
#define save32(buf, var) memcpy(buf, &var, 4)
#define save64(buf, var) memcpy(buf, &var, 8)

#define load16(var, buf) memcpy(&var, buf, 2)
#define load32(var, buf) memcpy(&var, buf, 4)
#define load64(var, buf) memcpy(&var, buf, 8)

/* lib6502 save state info uses arrays of bytes to maintain compatibility
 across platforms. Some platforms may have different alignment rules, so
 forcing as an array of bytes of the proper size works around this. */

typedef struct {
        uint64_t cycles_since_power_on;
        uint64_t instructions_since_power_on;
        uint32_t frame_number;
        uint32_t current_cycle_in_frame;
        uint32_t final_cycle_in_frame;
        uint32_t current_instruction_in_frame;

        uint8_t frame_status;
        uint8_t breakpoint_id;
        uint8_t unused1;
        uint8_t unused2;

        uint8_t memory_access[MAIN_MEMORY_SIZE];
        uint8_t access_type[MAIN_MEMORY_SIZE];

        uint8_t PC[2];
        uint8_t A;
        uint8_t X;
        uint8_t Y;
        uint8_t SP;
        uint8_t SR;

        uint8_t memory[1<<16];
} output_t;

extern long cycles_per_frame;

/* library functions defined in lib6502.c */

void lib6502_init_cpu(float frequency_mhz, float refresh_rate_hz);

void lib6502_get_current_state(output_t *output);

void lib6502_restore_state(output_t *output);

int lib6502_step_cpu();

int lib6502_next_frame(void *input, output_t *output, breakpoints_t *state);
