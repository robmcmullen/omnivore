/* Handwritten parsers */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "libemu.h"


int parse_entry_data(op_record_t *first, unsigned char *src, uint32_t *order, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;
    op_record_t *op = first;
    unsigned char flag = 0;

    first->type = 0x10;
    first->num = 1;
    first->payload.word = (unsigned short)pc;
    op++; /* reserve space for at least 4 bytes of "opcode" */
    first_instruction_ptr = (unsigned char *)op;
    
    unsigned char opcode = src[order[0]];
    while ((pc + first->num < last_pc) && (first->num < 255)) {
        if (src[order[first->num]] == opcode) first->num += 1;
        else break;
    }
    if (first->num <= 8) {
        unsigned leftmost = first->num;
        first->num = 8;
        if (pc + first->num > last_pc) {
            /* end of data; no need to check for a run at the end */
            first->num = last_pc - pc;
        }
        else if (pc + first->num < last_pc) {
            /* check end of entry to see if it starts a new run */
            unsigned int left = first->num;
            unsigned int right = left;
            unsigned next_opcode = src[order[left]];  /* next entry */
            while ((left > leftmost) && (src[order[left-1]] == next_opcode)) left--;  /* find first that matches next_opcode */
            if (left < 8) {
                /* last X bytes matched next byte. Check if next set will result in a run */
                right++;
                while ((src[order[right]] == next_opcode) && (pc + right < last_pc)) right++;
                if (right > left + 8) {
                    /* force early end so next call will pick up the run */
                    first->num = left;
                }
            }
        }
    }
    switch(first->num) {
    case 8:
        *first_instruction_ptr++ = src[*order++];
    case 7:
        *first_instruction_ptr++ = src[*order++];
    case 6:
        *first_instruction_ptr++ = src[*order++];
    case 5:
        *first_instruction_ptr++ = src[*order++];
        op++; /* need 2nd record to hold bytes 5 - 8 */
    case 4:
        *first_instruction_ptr++ = src[*order++];
    case 3:
        *first_instruction_ptr++ = src[*order++];
    case 2:
        *first_instruction_ptr++ = src[*order++];
    case 1:
        *first_instruction_ptr++ = src[*order++];
        break;
    default:
        *first_instruction_ptr = opcode;
        flag = FLAG_REPEATED_BYTES;
        break;
    }
    op++;
    op->type = 0xff;
    op->num = DISASM_DATA;
    op->payload.byte[0] = 0;
    op->payload.byte[1] = flag;
    return op - first + 1;
}

int parse_entry_antic_dl(op_record_t *first, unsigned char *src, uint32_t *order, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;
    unsigned short addr;
    op_record_t *op = first;
    unsigned char flag = 0;

    first->type = 0x10;
    first->num = 1;
    first->payload.word = (unsigned short)pc;
    op++; /* reserve space for at least 4 bytes of "opcode" */
    first_instruction_ptr = (unsigned char *)op;

    unsigned char opcode = src[order[0]];

    if (((opcode & 0x0f) == 1) || ((opcode & 0xf0) == 0x40)) {
        first->num = 3;
        if (pc + first->num > last_pc) {
            first->num = last_pc - pc;
        }
        else {
            addr = (256 * src[2]) + src[1];
            labels[addr] = DISASM_ANTIC_DL;
            flag = FLAG_TARGET_ADDR;
            op++;
            op->type = 0x30;
            op->num = flag;
            op->payload.word = addr;
        }
    }
    else {
        while (pc + first->num < last_pc) {
            if (src[first->num] == opcode) first->num += 1;
            else break;
        }
    }
    switch(first->num) {
    case 3:
        *first_instruction_ptr++ = src[*order++];
    case 2:
        *first_instruction_ptr++ = src[*order++];
    case 1:
        *first_instruction_ptr = src[*order];
        break;
    default:
        *first_instruction_ptr = opcode;
        flag = FLAG_REPEATED_BYTES;
        break;
    }
    op++;
    op->type = 0xff;
    op->num = DISASM_ANTIC_DL;
    op->payload.byte[0] = 0;
    op->payload.byte[1] = flag;
    return op - first + 1;
}

int parse_entry_jumpman_harvest(op_record_t *first, unsigned char *src, uint32_t *order, unsigned int pc, unsigned int last_pc, unsigned short *labels) {
    unsigned char *first_instruction_ptr;
    op_record_t *op = first;

    first->type = 0x10;
    first->payload.word = (unsigned short)pc;
    op++; /* reserve space for at least 4 bytes of "opcode" */
    first_instruction_ptr = (unsigned char *)op;
    
    unsigned char opcode = src[order[0]];

    if (opcode == 0xff) {
        first->num = 1;
    }
    else if (pc + 7 <= last_pc) {
        first->num = 7;
    }
    else {
        first->num = 1;
    }
    switch(first->num) {
    case 7:
        *first_instruction_ptr++ = src[*order++];
    case 6:
        *first_instruction_ptr++ = src[*order++];
    case 5:
        *first_instruction_ptr++ = src[*order++];
        op++;  /* need 2nd record to hold bytes 5 - 7 */
    case 4:
        *first_instruction_ptr++ = src[*order++];
    case 3:
        *first_instruction_ptr++ = src[*order++];
    case 2:
        *first_instruction_ptr++ = src[*order++];
    default:
        *first_instruction_ptr++ = src[*order++];
        break;
    }
    op++;
    op->type = 0xff;
    op->num = DISASM_JUMPMAN_HARVEST;
    op->payload.byte[0] = 0;
    op->payload.byte[1] = 0;
    return op - first + 1;
}
