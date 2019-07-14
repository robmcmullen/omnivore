#ifndef _LIBCRABAPPLE_H_
#define _LIBCRABAPPLE_H_

#include <stdint.h>
#include "6502-emu_wrapper.h"

/* Apple ][ graphics */

extern int hires_graphics;  /* 0 = lo res, 1 = hi res */
extern int text_mode; /* 0 = graphics, 1 = text */
extern int mixed_mode; /* 0 = full screen, 1 = text window */
extern int alt_page_select; /* 0 = page 1, 1 = page 2 */
extern int tv_line;
extern int tv_cycle;

/* First tv_line to start copying hires data to output. Arbitrary at this
   point, based on where the ANTIC from the Atari 800 starts*/
#define FIRST_OUTPUT_SCAN_LINE 40

/* First cycle of horizontal scan to start copying bytes to display memory */
#define FIRST_OUTPUT_CYCLE 12

#define SCAN_LINE_HIRES 0
#define SCAN_LINE_LORES 1
#define SCAN_LINE_TEXT 2
#define SCAN_LINE_DOUBLE_HIRES 0x80
#define SCAN_LINE_DOUBLE_LORES 0x81

extern uint16_t hgr_page1[];
extern uint16_t hgr_page2[];

void liba2_init_graphics();
void liba2_get_current_state(a2_output_t *buf);
void liba2_restore_state(a2_output_t *buf);
void liba2_read_softswitch(uint16_t addr);
void liba2_write_softswitch(uint16_t addr);
void liba2_copy_video(a2_output_t *output, uint8_t inst_cycles);

#endif /* _LIBCRABAPPLE_H_ */