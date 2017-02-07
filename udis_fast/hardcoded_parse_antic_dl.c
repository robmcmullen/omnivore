#include <stdio.h>
#include <string.h>

/* 12 byte structure */
typedef struct {
    unsigned short pc;
    unsigned short dest_pc; /* address pointed to by this opcode; if applicable */
    unsigned char count;
    unsigned char flag;
    unsigned char strlen;
    unsigned char reserved;
    int strpos; /* position of start of text in instruction array */
} asm_entry;

int parse_instruction_c_LL(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, unsigned char *instructions, int strpos) {
    unsigned char opcode;
    unsigned int num_printed = 0;
    int dli = 0;
    char *mnemonic;

    wrap->pc = (unsigned short)pc;
    wrap->strpos = strpos;
    wrap->flag = 0;
    wrap->count = 1;
    opcode = src[wrap->count - 1];

    if ((opcode & 0x0f == 1) || (opcode & 0xf0 == 0x40)) {
        wrap->count = 3;
        if (pc + wrap->count > last_pc) {
            wrap->count = pc + wrap->count - last_pc;
        }
    }
    else {
        while (pc + wrap->count < last_pc) {
            if (src[wrap->count] == opcode) wrap->count += 1;
            else break;
        }
    }

    if ((opcode & 0xf) == 1) {
        if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
        if (opcode & 0x40) mnemonic = "JVB";
        else if (opcode & 0xf0 > 0) mnemonic = "<invalid>";
        else mnemonic = "JMP";
        if (wrap->count < 3) num_printed += sprintf(instructions + num_printed, "%s <bad addr>", mnemonic);
        else num_printed += sprintf(instructions + num_printed, "%s %02x%02x", mnemonic, src[2], src[1]);
    }
    else {
        if (opcode & 0xf == 0) {
            if (wrap->count > 1) num_printed += sprintf(instructions + num_printed, "%dx", wrap->count);
            if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
            num_printed += sprintf(instructions + num_printed, "%d BLANK", (((opcode >> 4) & 0x07) + 1));
        }
        else {
            if (opcode & 0x40) {
                if (wrap->count < 3) num_printed += sprintf(instructions + num_printed, "LMS <bad addr> ");
                else num_printed += sprintf(instructions + num_printed, "LMS %02x%02x", src[2], src[1]);
            }
            else if (wrap->count > 1) num_printed += sprintf(instructions + num_printed, "%dx", wrap->count);

            if (opcode & 0x80) num_printed += sprintf(instructions + num_printed, "DLI ");
            if (opcode & 0x20) num_printed += sprintf(instructions + num_printed, "VSCROL ");
            if (opcode & 0x10) num_printed += sprintf(instructions + num_printed, "HSCROL ");

            num_printed += sprintf(instructions + num_printed, "MODE %X", (opcode & 0x0f));
        }
    }

    wrap->strlen = num_printed;
    return wrap->count;
}

int parse_instruction_c_LU(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, unsigned char *instructions, int strpos) {

    return parse_instruction_c_LL(wrap, src, pc, last_pc, labels, instructions, strpos);
}

int parse_instruction_c_UL(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, unsigned char *instructions, int strpos) {

    return parse_instruction_c_LL(wrap, src, pc, last_pc, labels, instructions, strpos);
}

int parse_instruction_c_UU(asm_entry *wrap, unsigned char *src, unsigned int pc, unsigned int last_pc, unsigned short *labels, unsigned char *instructions, int strpos) {

    return parse_instruction_c_LL(wrap, src, pc, last_pc, labels, instructions, strpos);
}
