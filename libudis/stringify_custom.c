/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"


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
