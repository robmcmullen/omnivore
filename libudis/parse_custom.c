/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"


int parse_entry_data(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->flag = FLAG_DATA_BYTES;
    entry->disassembler_type = DISASM_DATA;
    
    entry->num_bytes = 8;
    if (pc + entry->num_bytes > last_pc) {
        entry->num_bytes = last_pc - pc;
        if (entry->num_bytes == 0) {
            return 0;
        }
    }
    switch(entry->num_bytes) {
    case 8:
        *first_instruction_ptr++ = *src++;
    case 7:
        *first_instruction_ptr++ = *src++;
    case 6:
        *first_instruction_ptr++ = *src++;
    case 5:
        *first_instruction_ptr++ = *src++;
    case 4:
        *first_instruction_ptr++ = *src++;
    case 3:
        *first_instruction_ptr++ = *src++;
    case 2:
        *first_instruction_ptr++ = *src++;
    default:
        *first_instruction_ptr++ = *src++;
        break;
    }
    return entry->num_bytes;
}

int parse_entry_antic_dl(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->flag = FLAG_DATA_BYTES;
    entry->disassembler_type = DISASM_ANTIC_DL;
    
    entry->num_bytes = 1;
    unsigned char opcode = src[0];

    if (((opcode & 0x0f) == 1) || ((opcode & 0xf0) == 0x40)) {
        entry->num_bytes = 3;
        if (pc + entry->num_bytes > last_pc) {
            entry->num_bytes = last_pc - pc;
        }
    }
    else {
        while ((pc + entry->num_bytes < last_pc) && (entry->num_bytes < 16)) {
            if (src[entry->num_bytes] == opcode) entry->num_bytes += 1;
            else break;
        }
    }
    switch(entry->num_bytes) {
    case 16:
        *first_instruction_ptr++ = *src++;
    case 15:
        *first_instruction_ptr++ = *src++;
    case 14:
        *first_instruction_ptr++ = *src++;
    case 13:
        *first_instruction_ptr++ = *src++;
    case 12:
        *first_instruction_ptr++ = *src++;
    case 11:
        *first_instruction_ptr++ = *src++;
    case 10:
        *first_instruction_ptr++ = *src++;
    case 9:
        *first_instruction_ptr++ = *src++;
    case 8:
        *first_instruction_ptr++ = *src++;
    case 7:
        *first_instruction_ptr++ = *src++;
    case 6:
        *first_instruction_ptr++ = *src++;
    case 5:
        *first_instruction_ptr++ = *src++;
    case 4:
        *first_instruction_ptr++ = *src++;
    case 3:
        *first_instruction_ptr++ = *src++;
    case 2:
        *first_instruction_ptr++ = *src++;
    default:
        *first_instruction_ptr++ = *src++;
        break;
    }
    return entry->num_bytes;
}

int parse_entry_jumpman_harvest(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->flag = FLAG_DATA_BYTES;
    entry->disassembler_type = DISASM_JUMPMAN_HARVEST;
    
    unsigned char opcode = src[0];

    if (opcode == 0xff) {
        entry->num_bytes = 1;
    }
    else if (pc + 7 <= last_pc) {
        entry->num_bytes = 7;
    }
    else {
        entry->num_bytes = 1;
    }
    switch(entry->num_bytes) {
    case 7:
        *first_instruction_ptr++ = *src++;
    case 6:
        *first_instruction_ptr++ = *src++;
    case 5:
        *first_instruction_ptr++ = *src++;
    case 4:
        *first_instruction_ptr++ = *src++;
    case 3:
        *first_instruction_ptr++ = *src++;
    case 2:
        *first_instruction_ptr++ = *src++;
    default:
        *first_instruction_ptr++ = *src++;
        break;
    }
    return entry->num_bytes;
}
