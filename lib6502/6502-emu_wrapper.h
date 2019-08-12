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

/* lib6502 save state info uses arrays of bytes to maintain compatibility
 across platforms. Some platforms may have different alignment rules, so
 forcing as an array of bytes of the proper size works around this. */

typedef struct {
    frame_status_t status;

    /* group must equal 256 bytes */
    uint8_t PC[2];
    uint8_t A;
    uint8_t X;
    uint8_t Y;
    uint8_t SP;
    uint8_t SR;
    uint8_t unused1[249];

    uint8_t memory[1<<16];
} output_t;

typedef struct {
    frame_status_t status;

    /* group must equal 256 bytes */
    uint8_t PC[2];
    uint8_t A;
    uint8_t X;
    uint8_t Y;
    uint8_t SP;
    uint8_t SR;
    uint8_t unused1[249];

    uint8_t memory[1<<16];

    /* group must equal 256 bytes */
    uint8_t hires_graphics;
    uint8_t text_mode;
    uint8_t mixed_mode;
    uint8_t alt_page_select;
    uint8_t tv_line;
    uint8_t tv_cycle;
    uint8_t unused2[250];

    uint8_t video[40*192];
    uint8_t scan_line_type[192];
    uint8_t audio[2048];
} a2_output_t;

extern long cycles_per_frame;

/* library functions defined in lib6502.c */

void lib6502_init_cpu(int scan_lines, int cycles_per_scan_line);

void lib6502_get_current_state(output_t *output);

void lib6502_restore_state(output_t *output);

int lib6502_register_callback(uint16_t token, uint16_t addr);

int lib6502_step_cpu(output_t *output, history_6502_t *entry, breakpoints_t *breakpoints);

int lib6502_next_frame(history_input_t *input, output_t *output, breakpoints_t *state, emulator_history_t *history);

void lib6502_show_next_instruction(emulator_history_t *history);

#endif /* _6502_EMU_WRAPPER_H_ */
