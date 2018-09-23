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
	uint8_t disassembler_type;
	uint8_t unused;
	uint8_t instruction[16];
} history_entry_t; /* 12 bytes */

typedef struct {
	uint16_t pc;
	uint16_t target_addr;
	uint8_t num_bytes;
	uint8_t flag;
	uint8_t disassembler_type;
	uint8_t unused;
	uint8_t instruction[4];
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
	uint8_t extra[2];
} history_6502_entry_t; /* 24 bytes */


/* flags */
#define FLAG_BRANCH 1
#define FLAG_JUMP 2
#define FLAG_RTS 3
#define FLAG_RTI 4
#define FLAG_ORIGIN 5
#define FLAG_DATA_BYTES 6
#define FLAG_WRITE_ONE 7
#define FLAG_WRITE_TWO 8
#define FLAG_WRITE_THREE 9
#define FLAG_REPEATED_BYTES 10
#define FLAG_TARGET_ADDR 32
#define FLAG_LABEL 64
#define FLAG_UNDOC 128

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

#endif /* LIBUDIS_H */
