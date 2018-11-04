#ifndef _6502_EMU_WRAPPER_H_
#define _6502_EMU_WRAPPER_H_

#include <stdint.h>

#include "6502.h"
#include "libdebugger.h"
#include "libudis.h"

/* variables internal to 6502.c that we need to see */

extern int lengths[];

extern Instruction inst;

extern int jumping;

extern void *write_addr;
extern void *read_addr;

/* macros to save variables to (possibly unaligned) data buffer */

#define save16(buf, var) memcpy(buf, &var, 2)
#define save32(buf, var) memcpy(buf, &var, 4)
#define save64(buf, var) memcpy(buf, &var, 8)

#define load16(var, buf) memcpy(&var, buf, 2)
#define load32(var, buf) memcpy(&var, buf, 4)
#define load64(var, buf) memcpy(&var, buf, 8)

typedef struct {
    uint8_t keychar;
    uint8_t keycode;
    uint8_t special;
    uint8_t shift;
    uint8_t control;
    uint8_t start;
    uint8_t select;
    uint8_t option;
    uint8_t joy0;
    uint8_t trig0;
    uint8_t joy1;
    uint8_t trig1;
    uint8_t joy2;
    uint8_t trig2;
    uint8_t joy3;
    uint8_t trig3;
    uint8_t mousex;
    uint8_t mousey;
    uint8_t mouse_buttons;
    uint8_t mouse_mode;
} input_t;

/* lib6502 save state info uses arrays of bytes to maintain compatibility
 across platforms. Some platforms may have different alignment rules, so
 forcing as an array of bytes of the proper size works around this. */

typedef struct {
    frame_status_t status;

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

int lib6502_register_callback(uint16_t token, uint16_t addr);

int lib6502_step_cpu(frame_status_t *output, history_6502_t *entry, breakpoints_t *breakpoints);

int lib6502_next_frame(input_t *input, output_t *output, breakpoints_t *state, emulator_history_t *history);

void lib6502_show_next_instruction(emulator_history_t *history);

#endif /* _6502_EMU_WRAPPER_H_ */
