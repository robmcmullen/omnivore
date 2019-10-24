#ifndef LIBUDIS_H
#define LIBUDIS_H
#include <stdint.h>

#include "libudis_flags.h"

/* The history structure must match the definition in omni8bit/disassembler/dtypes.py */

/* cycles

	abaaaccc

	a: 1 = target addr is used, 0 = not
	b: 1 = target addr is write, 0 = not
	c = number of cycles (0 - 7)
*/

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t cycles;
	uint8_t instruction[16];
} history_entry_t; /* 24 bytes */

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t cycles;
	uint8_t instruction[3];
	uint8_t a;
	uint8_t x;
	uint8_t y;
	uint8_t sp;
	uint8_t sr;
	uint8_t before1;
	uint8_t after1;
	uint8_t before2;
	uint8_t after2;
	uint8_t before3;
	uint8_t after3;
	uint8_t tv_cycle;
	uint8_t tv_line;
} history_6502_t; /* 24 bytes */

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t cycles;
	uint8_t instruction[3];
	uint8_t a;
	uint8_t x;
	uint8_t y;
	uint8_t sp;
	uint8_t sr;
	uint8_t before1;
	uint8_t after1;
	uint8_t before2;
	uint8_t after2;
	uint8_t before3;
	uint8_t after3;
	uint8_t tv_cycle;
	uint8_t tv_line;
} history_atari800_t; /* 24 bytes */

typedef struct {
	uint32_t frame_number;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t cycles;
	uint8_t instruction[16];
} history_frame_t; /* 24 bytes */

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t cycles;
	uint8_t instruction[14];
	uint8_t tv_cycle;
	uint8_t tv_line;
} history_interrupt_t; /* 24 bytes */

typedef struct {
	uint16_t pc;
	uint8_t breakpoint_id;
	uint8_t breakpoint_type;
	uint8_t num_bytes;
	uint8_t disassembler_type;
	uint8_t flag;
	uint8_t disassembler_type_cpu;
	uint8_t instruction[16];
} history_breakpoint_t; /* 24 bytes */

typedef struct {
	uint8_t keychar;  /* ascii key value, 0 = no key press */
	uint8_t keycode;  /* keyboard code, 0 = no key press */
	uint8_t special_key;  /* non-standard key (option, select, etc.), */
	uint8_t flags;  /* platform dependent */
	uint8_t joystick_triggers;  /* bit 0 = trig 0, bit 1 = trig 1, etc. */
	uint8_t joysticks[2];  /* byte 0, bit 0-3 = joystick 0, bit 4-7 = joystick 1, byte 1, bit 0-3 = joystick 2, bit 4-7 = joystick 3 */
	uint8_t paddle_triggers;  /* same as joystick triggers */
	uint8_t paddles[8];  /* one byte each, paddles 0 - 7 */
	uint8_t mouse_x;
	uint8_t mouse_y;
	uint8_t mouse_buttons;
	uint8_t unused[5];
} history_input_t; /* 24 bytes */

typedef struct {
	int32_t num_allocated_entries;
	int32_t num_entries;
	int32_t first_entry_index;
	int32_t latest_entry_index;
	uint32_t cumulative_count;
	history_entry_t *entries;
} emulator_history_t;

typedef struct {
    uint32_t text_start_index;  /* offset into label character storage */
    int8_t line_length;  /* length of label in bytes; there is no delimiter */
    int8_t num_bytes; /* number of bytes of data */
    int8_t item_count; /* number of items in the data */
    int8_t type_code;  /* xxxxxxyy; display code = x, bytes_per_item = y + 1 (1 - 4 bytes per item) */
} label_info_t;

typedef struct {
	uint8_t text_length;  /* length of label in bytes; there is no delimiter */
	uint8_t num_bytes; /* number of bytes of data */
	uint8_t item_count; /* number of items in the data */
	uint8_t type_code;  /* xxxxxxyy; display code = x, bytes_per_item = y + 1 (1 - 4 bytes per item) */
	char label[12];
} label_description_t;

typedef struct {
	uint16_t flags;  /* xy000000 00000000; x = valid for read only, y = valid write only */
	uint16_t first_addr;  /* first 16 bit address with label */
	uint16_t last_addr;  /* last 16 bit address with label */
	uint16_t num_labels;  /* number of labels (same as last_addr - first_addr + 1, precomputed for speed) */
	uint16_t index[256*256];  /* index into 16-byte table of label descriptions, long labels may span multpile entries, zero indicates no label */
	label_description_t labels[1024]; /* label storage */
} label_storage_t;

typedef struct {
	uint8_t discovered[256*256];
	label_storage_t *labels;
} jmp_targets_t;

extern int print_label_or_addr(int addr, jmp_targets_t *jmp_targets, char *t, char *hexdigits, int zero_page);

typedef int (*string_func_t)(history_entry_t *, char *, char *, int, jmp_targets_t *);

extern char opcode_history_flags_6502[256];

extern char instruction_length_6502[256];

history_entry_t *libudis_get_next_entry(emulator_history_t *history, int type);


#endif /* LIBUDIS_H */
