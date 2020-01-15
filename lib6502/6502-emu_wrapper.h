#ifndef _6502_EMU_WRAPPER_H_
#define _6502_EMU_WRAPPER_H_

#include <stdint.h>

#include "6502.h"


#include "libdebugger.h"
#include "libudis.h"

/* emulator ID = "6502" */
#define LIB6502_EMULATOR_ID 0x32303635

/* variables internal to 6502.c that we need to see */

extern int lengths[];

extern Instruction inst;

extern int jumping;

extern void *write_addr;
extern void *read_addr;

/* lib6502 save state info uses arrays of bytes to maintain compatibility
 across platforms. Some platforms may have different alignment rules, so
 forcing as an array of bytes of the proper size works around this. */

typedef struct {
    /* emulator info group must equal 64 bytes */
    uint32_t cycles_per_frame;
    uint16_t cycles_per_scan_line;
    uint8_t extra_cycles_in_previous_frame;
    uint8_t apple2_mode;
    uint8_t hires_graphics;
    uint8_t text_mode;
    uint8_t mixed_mode;
    uint8_t alt_page_select;
    uint8_t tv_line;
    uint8_t tv_cycle;
    uint8_t unused1[50];

    /* emulator CPU group must equal 64 bytes */
    uint8_t PC[2];
    uint8_t A;
    uint8_t X;
    uint8_t Y;
    uint8_t SP;
    uint8_t SR;
    uint8_t unused2[57];

    uint8_t memory[1<<16];
} lib6502_emulator_state_t;

/* library functions defined in lib6502.c */

void lib6502_init_cpu(int scan_lines, int cycles_per_scan_line);

int lib6502_cold_start(op_history_t *input);

void lib6502_import_frame(emulator_state_t *state);

emulator_state_t *lib6502_export_frame();

int lib6502_step_cpu();

int lib6502_next_frame(op_history_t *input);

op_history_t *lib6502_export_steps();

#endif /* _6502_EMU_WRAPPER_H_ */
