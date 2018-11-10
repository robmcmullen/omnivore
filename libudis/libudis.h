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
	uint8_t extra1;
	uint8_t extra2;
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
	uint8_t antic_xpos;
	uint8_t antic_ypos;
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
	uint8_t instruction[16];
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
	int32_t num_allocated_entries;
	int32_t num_entries;
	int32_t first_entry_index;
	int32_t latest_entry_index;
	uint32_t cumulative_count;
	history_entry_t *entries;
} emulator_history_t;

typedef struct {
    uint32_t text_start_index;
    int8_t line_length;
    int8_t num_bytes;
    int8_t item_count;
    int8_t type_code;  /* xxxxxxyy; display code = x, bytes_per_item = y + 1 */
} label_info_t;

typedef struct {
	uint8_t discovered[256*256];
	char *text_storage;
	label_info_t *labels;
} jmp_targets_t;

extern int print_label_or_addr(int addr, jmp_targets_t *jmp_targets, char *t, char *hexdigits, int zero_page);

typedef int (*string_func_t)(history_entry_t *, char *, char *, int, jmp_targets_t *);

extern char opcode_history_flags_6502[256];

extern char instruction_length_6502[256];

history_entry_t *libudis_get_next_entry(emulator_history_t *history, int type);


#endif /* LIBUDIS_H */
