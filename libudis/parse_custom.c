/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"


int parse_entry_data(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->disassembler_type = DISASM_DATA;
    
    unsigned char opcode = src[0];
    entry->num_bytes = 1;
    while ((pc + entry->num_bytes < last_pc) && (entry->num_bytes < 255)) {
        if (src[entry->num_bytes] == opcode) entry->num_bytes += 1;
        else break;
    }
    if (entry->num_bytes <= 8) {
        unsigned leftmost = entry->num_bytes;
        entry->num_bytes = 8;
        if (pc + entry->num_bytes > last_pc) {
            /* end of data; no need to check for a run at the end */
            entry->num_bytes = last_pc - pc;
        }
        else if (pc + entry->num_bytes < last_pc) {
            /* check end of entry to see if it starts a new run */
            unsigned int left = entry->num_bytes;
            unsigned int right = left;
            unsigned next_opcode = src[left];  /* next entry */
            while ((left > leftmost) && (src[left-1] == next_opcode)) left--;  /* find first that matches next_opcode */
            if (left < 8) {
                /* last X bytes matched next byte. Check if next set will result in a run */
                right++;
                while ((src[right] == next_opcode) && (pc + right < last_pc)) right++;
                if (right > left + 8) {
                    /* force early end so next call will pick up the run */
                    entry->num_bytes = left;
                }
            }
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
    case 1:
        *first_instruction_ptr++ = *src++;
        break;
    default:
        *first_instruction_ptr = *src;
        entry->flag = FLAG_REPEATED_BYTES;
        break;
    }
    return entry->num_bytes;
}

int parse_entry_antic_dl(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;
    unsigned short addr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
    entry->flag = 0;
    entry->disassembler_type = DISASM_ANTIC_DL;
    
    entry->num_bytes = 1;
    unsigned char opcode = src[0];

    if (((opcode & 0x0f) == 1) || ((opcode & 0xf0) == 0x40)) {
        entry->num_bytes = 3;
        if (pc + entry->num_bytes > last_pc) {
            entry->num_bytes = last_pc - pc;
        }
        else {
            addr = (256 * src[2]) + src[1];
            labels[addr] = DISASM_ANTIC_DL;
            entry->target_addr = addr;
            entry->flag = FLAG_TARGET_ADDR;
        }
    }
    else {
        while (pc + entry->num_bytes < last_pc) {
            if (src[entry->num_bytes] == opcode) entry->num_bytes += 1;
            else break;
        }
    }
    switch(entry->num_bytes) {
    case 3:
        *first_instruction_ptr++ = *src++;
    case 2:
        *first_instruction_ptr++ = *src++;
    case 1:
        *first_instruction_ptr = *src;
        break;
    default:
        *first_instruction_ptr = *src;
        entry->flag = FLAG_REPEATED_BYTES;
        break;
    }
    return entry->num_bytes;
}

int parse_entry_jumpman_harvest(history_entry_t *entry, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;

    first_instruction_ptr = entry->instruction;
    entry->pc = (unsigned short)pc;
    entry->target_addr = 0;
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
