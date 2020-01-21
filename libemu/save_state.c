#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libemu/save_state.h"


emulator_state_t *create_emulator_state(int save_size, int input_size, int video_size, int audio_size) {
	emulator_state_t *buf;
	int total_size;

	total_size = sizeof(emulator_state_t) + save_size + input_size + video_size + audio_size;
	buf = (emulator_state_t *)malloc(total_size);
	buf->malloc_size = total_size;
    buf->magic = LIBEMU_SAVE_STATE_MAGIC;
    buf->frame_number = -1;
    buf->emulator_id = -1;
    buf->input_offset = sizeof(emulator_state_t);
    buf->input_size = input_size;
    buf->save_state_offset = buf->input_offset + input_size;
    buf->save_state_size = save_size;
    buf->video_offset = buf->save_state_offset + save_size;
    buf->video_size = video_size;
    buf->audio_offset = buf->video_offset + video_size;
    buf->audio_size = audio_size;

    return buf;
}
