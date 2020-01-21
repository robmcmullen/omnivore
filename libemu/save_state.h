#ifndef LIBEMU_SAVE_STATE_H
#define LIBEMU_SAVE_STATE_H
#include <stdint.h>


#define MAIN_MEMORY_SIZE (256*256)

#define LIBEMU_SAVE_STATE_MAGIC 0x6462606c

// macros to save variables to (possibly unaligned, possibly endian-swapped)
// data buffer. NOTE: endian-swappiness not actually handled yet, assuming
// little endian
#define save16(buf, var) memcpy(buf, &var, 2)
#define save32(buf, var) memcpy(buf, &var, 4)
#define save64(buf, var) memcpy(buf, &var, 8)

#define load16(var, buf) memcpy(&var, buf, 2)
#define load32(var, buf) memcpy(&var, buf, 4)
#define load64(var, buf) memcpy(&var, buf, 8)

// header for save state file. All emulators must use a save state format that
// uses this header; must be 128 bytes long to reserve space for future
// compatibilty
typedef struct {
    uint32_t malloc_size; /* size of structure in bytes */
    uint32_t magic; /* libdebugger magic number */
    uint32_t frame_number;
    uint32_t emulator_id; /* unique emulator ID number */

    // Frame input parameters
    uint32_t input_offset; /* number of bytes from start to user input history */
    uint32_t input_size; /* number of bytes in user input history */

    // Frame output parameters
    uint32_t save_state_offset; /* number of bytes from start to save state data */
    uint32_t save_state_size; /* number of bytes in save state data */

    uint32_t video_offset; /* number of bytes from start to video data */
    uint32_t video_size; /* number of bytes in video data */

    uint32_t audio_offset; /* number of bytes from start to audio data */
    uint32_t audio_size; /* number of bytes in audio data */

    uint8_t unused0[80];
} emulator_state_t;

#define INPUT_PTR(buf) ((char *)buf + buf->input_offset)
#define SAVE_STATE_PTR(buf) ((char *)buf + buf->save_state_offset)
#define VIDEO_PTR(buf) ((char *)buf + buf->video_offset)
#define AUDIO_PTR(buf) ((char *)buf + buf->audio_offset)

emulator_state_t *create_emulator_state(int save_size, int input_size, int video_size, int audio_size);

#endif /* LIBEMU_SAVE_STATE_H */
