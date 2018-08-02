#include <stdint.h>

#include "libdebugger.h"

#include "config.h"
#include "atari.h"
#include "screen.h"
#ifdef SOUND
#include "sound.h"
#endif
#include "libatari800/statesav.h"


#define Screen_USABLE_WIDTH 336

#define LIBATARI800_VIDEO_SIZE (Screen_USABLE_WIDTH * Screen_HEIGHT)
#define LIBATARI800_SOUND_SIZE 2048


typedef struct {
    frame_status_t status;
    uint8_t video[LIBATARI800_VIDEO_SIZE];
    uint8_t audio[LIBATARI800_SOUND_SIZE];
    statesav_tags_t tags;
    uint8_t state[STATESAV_MAX_SIZE];
} output_template_t;

extern long cycles_per_frame;


/*
vim:ts=4:sw=4:
*/

