#ifndef _ATARI800_BRIDGE_H_
#define _ATARI800_BRIDGE_H_

#include <stdint.h>

#include "libdebugger.h"
#include "libudis.h"

#include "config.h"
#include "atari.h"
#include "screen.h"
#ifdef SOUND
#include "sound.h"
#endif
#include "libatari800/libatari800.h"


#define Screen_USABLE_WIDTH 336

#define LIBATARI800_VIDEO_SIZE (Screen_USABLE_WIDTH * Screen_HEIGHT)
#define LIBATARI800_SOUND_SIZE 2048


typedef struct {
    frame_status_t status;
    uint8_t video[LIBATARI800_VIDEO_SIZE];
    uint8_t audio[LIBATARI800_SOUND_SIZE];
    emulator_state_t current;
} output_template_t;

extern long cycles_per_frame;

extern int nmi_changing;
extern int last_nmi_type;

extern emulator_history_t *LIBATARI800_History;


void ANTIC_Frame2(frame_status_t *status);

int a8bridge_register_callback(uint16_t token, uint16_t addr);

/*
vim:ts=4:sw=4: 
*/

#endif /* _ATARI800_BRIDGE_H_ */
