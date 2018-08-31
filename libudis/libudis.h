#ifndef LIBUDIS_H
#define LIBUDIS_H
#include <stdint.h>

/* The history structure must match the definition in omni8bit/udis_fast/dtypes.py */

/* default 32k entries, plenty for one frame */
#define HISTORY_ENTRIES (256 * 128)

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t flag;
	uint8_t instruction[3];
	uint8_t a;
	uint8_t x;
	uint8_t y;
	uint8_t sp;
	uint8_t sr;
	uint8_t byte1_before;
	uint8_t byte1_after;
	uint8_t byte2_before;
	uint8_t byte2_after;
} history_entry_t;

/* affected address flags */
#define HISTORY_WRITE_NONE 0
#define HISTORY_WRITE_ONE 1
#define HISTORY_WRITE_TWO 2
#define HISTORY_WRITE_THREE 3

#define HISTORY_LOAD 0
#define HISTORY_SAVE (1 << 2)
#define HISTORY_JUMP (2 << 2)
#define HISTORY_RETURN (3 << 2)


#endif /* LIBUDIS_H */
