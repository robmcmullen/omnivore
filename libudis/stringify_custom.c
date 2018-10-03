/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"
#include "stringify_udis_cpu.h"


int stringify_entry_data(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    char *first_t, *h;
    unsigned char *data;

    first_t = t;
    data = entry->instruction;
    if (lc) *t++='.', *t++='b', *t++='y', *t++='t', *t++='e', *t++=' ';
    else *t++='.', *t++='B', *t++='Y', *t++='T', *t++='E', *t++=' ';
    if (entry->flag == FLAG_REPEATED_BYTES) {
        t += sprintf(t, "%d", entry->num_bytes);
        *t++='*';
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    }
    else switch(entry->num_bytes) {
    case 8:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 7:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 6:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 5:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 4:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 3:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    case 2:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    default:
        h = &hexdigits[(*data++ & 0xff)*2]; *t++=*h++; *t++=*h++;
    }
    return (int)(t - first_t);
}

int stringify_entry_antic_dl(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    unsigned char opcode;
    int i;
    char *first_t, *h;
    unsigned char *data;
    unsigned short addr;

    first_t = t;
    data = entry->instruction;
    opcode = *data;
    if (lc) *t++='.', *t++='a', *t++='n', *t++='t', *t++='i', *t++='c', *t++=' ';
    else *t++='.', *t++='A', *t++='N', *t++='T', *t++='I', *t++='C', *t++=' ';
    if ((opcode & 0xf) == 1) {
        if (opcode & 0x80) {
            if (lc) *t++='d', *t++='l', *t++='i';
            else *t++='D', *t++='L', *t++='I';
            *t++=' ';
        }
        if (opcode & 0x40) {
            if (lc) *t++='j', *t++='v', *t++='b';
            else *t++='J', *t++='V', *t++='B';
            *t++=' ';
        }
        else if ((opcode & 0xf0) > 0) {
            *t++='<';
            if (lc) *t++='i', *t++='n', *t++='v', *t++='a', *t++='l', *t++='i', *t++='d';
            else *t++='I', *t++='N', *t++='V', *t++='A', *t++='L', *t++='I', *t++='D';
            *t++='>';
        }
        else {
            if (lc) *t++='j', *t++='m', *t++='p';
            else *t++='j', *t++='m', *t++='p';
            *t++=' ';
        }
        if (entry->num_bytes < 3) {
            *t++='<';
            if (lc) *t++='b', *t++='a', *t++='d', *t++=' ', *t++='a', *t++='d', *t++='d', *t++='r';
            else *t++='B', *t++='A', *t++='D', *t++=' ', *t++='A', *t++='D', *t++='D', *t++='R';
            *t++='>';
        }
        else {
            addr = entry->target_addr;
            if (labels[addr]) {
                *t++='L';
                h = &hexdigits[(addr >> 8)*2]; *t++=*h++; *t++=*h++;
                h = &hexdigits[(addr & 0xff)*2]; *t++=*h++; *t++=*h++;
            }
            else {
                *t++='$';
                h = &hexdigits[(data[2] & 0xff)*2], *t++=*h++, *t++=*h++;
                h = &hexdigits[(data[1] & 0xff)*2], *t++=*h++, *t++=*h++;
            }
        }
    }
    else {
        if ((opcode & 0xf) == 0) {
            if (entry->num_bytes > 1) {
                t += sprintf(t, "%d", entry->num_bytes);
                *t++='*';
            }
            if (opcode & 0x80) {
                if (lc) *t++='d', *t++='l', *t++='i';
                else *t++='D', *t++='L', *t++='I';
                *t++=' ';
            }
            if (lc) *t++='b', *t++='l', *t++='a', *t++='n', *t++='k';
            else *t++='B', *t++='L', *t++='A', *t++='N', *t++='K';
            *t++=' ';
            t += sprintf(t, "%d", (((opcode >> 4) & 0x07) + 1));
        }
        else {
            if ((opcode & 0xf0) == 0x40) {
                if (lc) *t++='l', *t++='m', *t++='s';
                else *t++='L', *t++='M', *t++='S';
                *t++=' ';
                if (entry->num_bytes < 3) {
                    *t++='<';
                    if (lc) *t++='b', *t++='a', *t++='d', *t++=' ', *t++='a', *t++='d', *t++='d', *t++='r';
                    else *t++='B', *t++='A', *t++='D', *t++=' ', *t++='A', *t++='D', *t++='D', *t++='R';
                    *t++='>',*t++=' ';
                }
                else {
                    addr = entry->target_addr;
                    if (labels[addr]) {
                        *t++='L';
                        h = &hexdigits[(addr >> 8)*2]; *t++=*h++; *t++=*h++;
                        h = &hexdigits[(addr & 0xff)*2]; *t++=*h++; *t++=*h++;
                    }
                    else {
                        *t++='$';
                        h = &hexdigits[(data[2] & 0xff)*2], *t++=*h++, *t++=*h++;
                        h = &hexdigits[(data[1] & 0xff)*2], *t++=*h++, *t++=*h++;
                    }
                    *t++=' ';
                }
            }
            else if (entry->num_bytes > 1) {
                t += sprintf(t, "%d", entry->num_bytes);
                *t++='*';
            }
            if (opcode & 0x80) {
                if (lc) *t++='d', *t++='l', *t++='i';
                else *t++='D', *t++='L', *t++='I';
                *t++=' ';
            }
            if (opcode & 0x20) {
                if (lc) *t++='v', *t++='s', *t++='c', *t++='r', *t++='o', *t++='l', *t++='l';
                else *t++='V', *t++='S', *t++='C', *t++='R', *t++='O', *t++='L', *t++='L';
                *t++=' ';
            }
            if (opcode & 0x10) {
                if (lc) *t++='h', *t++='s', *t++='c', *t++='r', *t++='o', *t++='l', *t++='l';
                else *t++='H', *t++='S', *t++='C', *t++='R', *t++='O', *t++='L', *t++='L';
                *t++=' ';
            }
            if (lc) *t++='m', *t++='o', *t++='d', *t++='e';
            else *t++='M', *t++='O', *t++='D', *t++='E';
            *t++=' ';
            h = &hexdigits[((opcode & 0x0f) & 0xff)*2] + 1;
            *t++=*h++;
        }
    }
    return (int)(t - first_t);
}

int stringify_entry_jumpman_harvest(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    unsigned char opcode;
    char *first_t, *h;
    unsigned char *data;

    first_t = t;
    data = entry->instruction;
    opcode = *data;

    if (opcode == 0xff) {
        h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ',*t++=';',*t++=' ';
        if (lc) *t++='e',*t++='n',*t++='d';
        else *t++='E',*t++='N',*t++='D';
    }
    else if (entry->num_bytes == 7) {
        h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[1] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[2] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[3] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[4] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[5] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[6] & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ',*t++=';',*t++=' ';
        if (lc) *t++='e',*t++='n',*t++='c';
        else *t++='E',*t++='N',*t++='C';
        *t++='=',*t++='$';
        h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
        if (lc) *t++='x';
        else *t++='X';
        *t++='=',*t++='$';
        h = &hexdigits[(data[1] & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
        if (lc) *t++='y';
        else *t++='Y';
        *t++='=',*t++='$';
        h = &hexdigits[(data[2] & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
        if (lc) *t++='t',*t++='a',*t++='k',*t++='e';
        else *t++='T',*t++='A',*t++='K',*t++='E';
        *t++='=',*t++='$';
        h = &hexdigits[(data[4] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[3] & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
        if (lc) *t++='p',*t++='a',*t++='i',*t++='n',*t++='t';
        else *t++='P',*t++='A',*t++='I',*t++='N',*t++='T';
        *t++='=',*t++='$';
        h = &hexdigits[(data[6] & 0xff)*2]; *t++=*h++; *t++=*h++;
        h = &hexdigits[(data[5] & 0xff)*2]; *t++=*h++; *t++=*h++;
    }
    else {
        h = &hexdigits[(opcode & 0xff)*2]; *t++=*h++; *t++=*h++;
        *t++=' ',*t++=';',*t++=' ',*t++='[';
        if (lc) *t++='i',*t++='n',*t++='c',*t++='o',*t++='m',*t++='p',*t++='l',*t++='e',*t++='t',*t++='e';
        else *t++='I',*t++='N',*t++='C',*t++='O',*t++='M',*t++='P',*t++='L',*t++='E',*t++='T',*t++='E';
        *t++=']';
    }
    return (int)(t - first_t);
}

int stringify_entry_frame_start(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='S', *t++='t', *t++='a', *t++='r', *t++='t', *t++=' ', *t++='f', *t++='r', *t++='a', *t++='m', *t++='e', *t++=' ';
    t += sprintf(t, "%d", frame->frame_number);
    return (int)(t - first_t);
}

int stringify_entry_frame_end(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='E', *t++='n', *t++='d', *t++=' ', *t++='f', *t++='r', *t++='a', *t++='m', *t++='e', *t++=' ';
    t += sprintf(t, "%d", frame->frame_number);
    return (int)(t - first_t);
}

int stringify_entry_6502_history(history_entry_t *h_entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    int val;
    char *first_t, *h;
    history_6502_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    h = &hexdigits[(entry->a & 0xff)*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    h = &hexdigits[(entry->x & 0xff)*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    h = &hexdigits[(entry->y & 0xff)*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    val = entry->sr;
    if (val & 0x80) *t++='N'; else *t++='-';
    if (val & 0x40) *t++='V'; else *t++='-';
    *t++='-';
    if (val & 0x10) *t++='B'; else *t++='-';
    if (val & 0x8) *t++='D'; else *t++='-';
    if (val & 0x4) *t++='I'; else *t++='-';
    if (val & 0x2) *t++='Z'; else *t++='-';
    if (val & 0x1) *t++='C'; else *t++='-';
    *t++=' ';
    h = &hexdigits[(entry->sp & 0xff)*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    h = &hexdigits[(entry->pc >> 8)*2]; *t++=*h++; *t++=*h++;
    h = &hexdigits[(entry->pc & 0xff)*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    *t++=' ';
    h = &hexdigits[entry->instruction[0]*2]; *t++=*h++; *t++=*h++;
    *t++=' ';
    if (entry->num_bytes > 1) {
        h = &hexdigits[entry->instruction[1]*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
    }
    else *t++=' ', *t++=' ', *t++=' ';
    if (entry->num_bytes > 2) {
        h = &hexdigits[entry->instruction[2]*2]; *t++=*h++; *t++=*h++;
        *t++=' ';
    }
    else *t++=' ', *t++=' ', *t++=' ';
    *t++=' ';
    t += stringify_entry_6502(entry, t, hexdigits, lc, labels);
    return (int)(t - first_t);
}

int stringify_entry_6502_history_result(history_entry_t *h_entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    int val, changed;
    char *first_t, *h;
    history_6502_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    if (entry->flag == FLAG_BRANCH_TAKEN) {
        *t++='(', *t++='t', *t++='a', *t++='k', *t++='e', *t++='n', *t++=')';
    }
    else if (entry->flag == FLAG_BRANCH_NOT_TAKEN) {
        *t++='(', *t++='n', *t++='o', *t++='t', *t++=' ', *t++='t', *t++='a', *t++='k', *t++='e', *t++='n', *t++=')';
    }
    else if (entry->flag == FLAG_REG_A) {
        *t++='A', *t++='=';
        h = &hexdigits[entry->after1*2]; *t++=*h++; *t++=*h++;
    }
    else if (entry->flag == FLAG_REG_X) {
        *t++='X', *t++='=';
        h = &hexdigits[entry->after1*2]; *t++=*h++; *t++=*h++;
    }
    else if (entry->flag == FLAG_REG_Y) {
        *t++='Y', *t++='=';
        h = &hexdigits[entry->after1*2]; *t++=*h++; *t++=*h++;
    }
    else if (entry->flag == FLAG_REG_SR) {
        changed = entry->sr ^ entry->after1;
        val = entry->after1;
        if (changed & 0x80) {*t++=' '; *t++='N'; *t++='='; if (val&0x80) *t++='1'; else *t++='0';}
        if (changed & 0x40) {*t++=' '; *t++='V'; *t++='='; if (val&0x40) *t++='1'; else *t++='0';}
        if (changed & 0x10) {*t++=' '; *t++='B'; *t++='='; if (val&0x10) *t++='1'; else *t++='0';}
        if (changed & 0x8) {*t++=' '; *t++='D'; *t++='='; if (val&0x8) *t++='1'; else *t++='0';}
        if (changed & 0x4) {*t++=' '; *t++='I'; *t++='='; if (val&0x4) *t++='1'; else *t++='0';}
        if (changed & 0x2) {*t++=' '; *t++='Z'; *t++='='; if (val&0x2) *t++='1'; else *t++='0';}
        if (changed & 0x1) {*t++=' '; *t++='C'; *t++='='; if (val&0x1) *t++='1'; else *t++='0';}
    }
    else if (entry->flag == FLAG_READ_ONE) {
        *t++='R', *t++='e', *t++='a', *t++='d';
    }
    else if (entry->flag == FLAG_WRITE_ONE) {
        *t++='W', *t++='r', *t++='i', *t++='t', *t++='e';
    }
    return (int)(t - first_t);
}

int stringify_entry_unknown_disassembler(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    char *first_t;

    first_t = t;
    *t++='-', *t++='-', *t++='U', *t++='n', *t++='k', *t++='n', *t++='o', *t++='w', *t++='n', *t++=' ', *t++='h', *t++='i', *t++='s', *t++='t', *t++='o', *t++='r', *t++='y',  *t++=' ', *t++='t', *t++='y', *t++='p', *t++='e', *t++=' ';
    t += sprintf(t, "%d", entry->disassembler_type);
    return (int)(t - first_t);
}

int stringify_entry_blank(history_entry_t *entry, char *t, char *hexdigits, int lc, unsigned short *labels) {
    return 0;
}
