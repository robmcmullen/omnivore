#ifndef LIBEMU_DISASM_H
#define LIBEMU_DISASM_H

#include <stdint.h>

#include "op_history.h"

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

#define COMMENT_BIT_MASK 0x40

typedef int (*parse_func_t)(op_record_t *first, unsigned char *src, uint32_t *order, unsigned int pc, unsigned int last_pc, jmp_targets_t *jmp_targets);


extern void *parser_map[];


#endif /* LIBEMU_DISASM_H */
