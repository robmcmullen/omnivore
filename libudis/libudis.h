#ifndef LIBUDIS_H
#define LIBUDIS_H
#include <stdint.h>

/* The history structure must match the definition in omni8bit/udis_fast/dtypes.py */

/* default 32k entries, plenty for one frame */
#define HISTORY_ENTRIES (256 * 128)

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
	uint8_t before1_or_sr;
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
	uint8_t before1_or_sr;
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
	int32_t num_allocated_entries;
	int32_t num_entries;
	int32_t first_entry_index;
	int32_t latest_entry_index;
	uint32_t cumulative_count;
	history_entry_t *entries;
} emulator_history_t;


/* flags */
#define FLAG_BRANCH_TAKEN 1
#define FLAG_BRANCH_NOT_TAKEN 2
#define FLAG_JUMP 3
#define FLAG_RTS 4
#define FLAG_RTI 5
#define FLAG_ORIGIN 6
#define FLAG_DATA_BYTES 7
#define FLAG_WRITE_ONE 8
#define FLAG_WRITE_TWO 9
#define FLAG_WRITE_THREE 10
#define FLAG_READ_ONE 11
#define FLAG_REPEATED_BYTES 12
#define FLAG_REG_A 13
#define FLAG_REG_X 14
#define FLAG_REG_Y 15
#define FLAG_TARGET_ADDR 64
#define FLAG_REG_SR 128

#define FLAG_RESULT_MASK 0x3f

/* disassembler types */
#define DISASM_DATA 0
#define DISASM_6502 10
#define DISASM_6502UNDOC 11
#define DISASM_65816 12
#define DISASM_65C02 13
#define DISASM_6800 14
#define DISASM_6809 15
#define DISASM_6811 16
#define DISASM_8051 17
#define DISASM_8080 18
#define DISASM_Z80 19
#define DISASM_ANTIC_DL 30
#define DISASM_JUMPMAN_HARVEST 31
#define DISASM_JUMPMAN_LEVEL 32

/* types 128-191 are for history entries that have result entries */
#define DISASM_6502_HISTORY 128
#define DISASM_6502_HISTORY_RESULT 129
#define DISASM_ATARI800_HISTORY 130
#define DISASM_ATARI800_HISTORY_RESULT 131

/* types 192-254 don't have results */
#define DISASM_FRAME_START 192
#define DISASM_FRAME_END 193
#define DISASM_ATARI800_VBI_START 194
#define DISASM_ATARI800_VBI_END 195
#define DISASM_ATARI800_DLI_START 196
#define DISASM_ATARI800_DLI_END 197

#define DISASM_UNKNOWN 255

history_entry_t *libudis_get_next_entry(emulator_history_t *history, int type);


#endif /* LIBUDIS_H */
