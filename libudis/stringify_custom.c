/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"


int stringify_entry_data(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    char *first_txt, *h;
    unsigned char *data;

    first_txt = txt;
    data = entry->instruction;
    switch(entry->num_bytes) {
    case 8:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 7:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 6:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 5:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 4:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 3:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    case 2:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    default:
        h = &hexdigits[(*data++ & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        break;
    }
    return (int)(txt - first_txt);
}

int stringify_entry_antic_dl(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    unsigned char opcode;
    int i;
    char *first_txt, *h;
    unsigned char *data;

    first_txt = txt;
    data = entry->instruction;
    opcode = *data;
    *txt++ = '.', *txt++ = 'a', *txt++ = 'n', *txt++ = 't', *txt++ = 'i', *txt++ = 'c', *txt++ = ' ';
    if ((opcode & 0xf) == 1) {
        if (opcode & 0x80) {
            if (lc) *txt++ = 'd', *txt++ = 'l', *txt++ = 'i';
            else *txt++ = 'D', *txt++ = 'L', *txt++ = 'I';
            *txt++ = ' ';
        }
        if (opcode & 0x40) {
            if (lc) *txt++ = 'j', *txt++ = 'v', *txt++ = 'b';
            else *txt++ = 'J', *txt++ = 'V', *txt++ = 'B';
            *txt++ = ' ';
        }
        else if ((opcode & 0xf0) > 0) {
            *txt++ = '<';
            if (lc) *txt++ = 'i', *txt++ = 'n', *txt++ = 'v', *txt++ = 'a', *txt++ = 'l', *txt++ = 'i', *txt++ = 'd';
            else *txt++ = 'I', *txt++ = 'N', *txt++ = 'V', *txt++ = 'A', *txt++ = 'L', *txt++ = 'I', *txt++ = 'D';
            *txt++ = '>';
        }
        else {
            if (lc) *txt++ = 'j', *txt++ = 'm', *txt++ = 'p';
            else *txt++ = 'j', *txt++ = 'm', *txt++ = 'p';
            *txt++ = ' ';
        }
        if (entry->num_bytes < 3) {
            *txt++ = '<';
            if (lc) *txt++ = 'b', *txt++ = 'a', *txt++ = 'd', *txt++ = ' ', *txt++ = 'a', *txt++ = 'd', *txt++ = 'd', *txt++ = 'r';
            else *txt++ = 'B', *txt++ = 'A', *txt++ = 'D', *txt++ = ' ', *txt++ = 'A', *txt++ = 'D', *txt++ = 'D', *txt++ = 'R';
            *txt++ = '>';
        }
        else {
            *txt++ = '$';
            h = &hexdigits[(data[2] & 0xff)*2], *txt++ = *h++, *txt++ = *h++;
            h = &hexdigits[(data[1] & 0xff)*2], *txt++ = *h++, *txt++ = *h++;
        }
    }
    else {
        if ((opcode & 0xf) == 0) {
            if (entry->num_bytes > 1) {
                txt += sprintf(txt, "%d", entry->num_bytes);
                *txt++ = 120;
            }
            if (opcode & 0x80) {
                if (lc) *txt++ = 'd', *txt++ = 'l', *txt++ = 'i';
                else *txt++ = 'D', *txt++ = 'L', *txt++ = 'I';
                *txt++ = ' ';
            }
            if (lc) *txt++ = 'b', *txt++ = 'l', *txt++ = 'a', *txt++ = 'n', *txt++ = 'k';
            else *txt++ = 'B', *txt++ = 'L', *txt++ = 'A', *txt++ = 'N', *txt++ = 'K';
            *txt++ = ' ';
            txt += sprintf(txt, "%d", (((opcode >> 4) & 0x07) + 1));
        }
        else {
            if ((opcode & 0xf0) == 0x40) {
                if (lc) *txt++ = 'l', *txt++ = 'm', *txt++ = 's';
                else *txt++ = 'L', *txt++ = 'M', *txt++ = 'S';
                *txt++ = ' ';
                if (entry->num_bytes < 3) {
                    *txt++ = '<';
                    if (lc) *txt++ = 'b', *txt++ = 'a', *txt++ = 'd', *txt++ = ' ', *txt++ = 'a', *txt++ = 'd', *txt++ = 'd', *txt++ = 'r';
                    else *txt++ = 'B', *txt++ = 'A', *txt++ = 'D', *txt++ = ' ', *txt++ = 'A', *txt++ = 'D', *txt++ = 'D', *txt++ = 'R';
                    *txt++ = '>',*txt++ = ' ';
                }
                else {
                    *txt++ = '$';
                    h = &hexdigits[(data[2] & 0xff)*2], *txt++ = *h++, *txt++ = *h++;
                    h = &hexdigits[(data[1] & 0xff)*2], *txt++ = *h++, *txt++ = *h++;
                    *txt++ = ' ';
                }
            }
            else if (entry->num_bytes > 1) {
                txt += sprintf(txt, "%d", entry->num_bytes);
                *txt++ = 120;
            }
            if (opcode & 0x80) {
                if (lc) *txt++ = 'd', *txt++ = 'l', *txt++ = 'i';
                else *txt++ = 'D', *txt++ = 'L', *txt++ = 'I';
                *txt++ = ' ';
            }
            if (opcode & 0x20) {
                if (lc) *txt++ = 'v', *txt++ = 's', *txt++ = 'c', *txt++ = 'r', *txt++ = 'o', *txt++ = 'l', *txt++ = 'l';
                else *txt++ = 'V', *txt++ = 'S', *txt++ = 'C', *txt++ = 'R', *txt++ = 'O', *txt++ = 'L', *txt++ = 'L';
                *txt++ = ' ';
            }
            if (opcode & 0x10) {
                if (lc) *txt++ = 'h', *txt++ = 's', *txt++ = 'c', *txt++ = 'r', *txt++ = 'o', *txt++ = 'l', *txt++ = 'l';
                else *txt++ = 'H', *txt++ = 'S', *txt++ = 'C', *txt++ = 'R', *txt++ = 'O', *txt++ = 'L', *txt++ = 'L';
                *txt++ = ' ';
            }
            if (lc) *txt++ = 'm', *txt++ = 'o', *txt++ = 'd', *txt++ = 'e';
            else *txt++ = 'M', *txt++ = 'O', *txt++ = 'D', *txt++ = 'E';
            *txt++ = ' ';
            h = &hexdigits[((opcode & 0x0f) & 0xff)*2] + 1;
            *txt++ = *h++;
        }
    }
    return (int)(txt - first_txt);
}

int stringify_entry_jumpman_harvest(history_entry_t *entry, char *txt, char *hexdigits, int lc) {
    unsigned char opcode;
    char *first_txt, *h;
    unsigned char *data;

    first_txt = txt;
    data = entry->instruction;
    opcode = *data;

    if (opcode == 0xff) {
        h = &hexdigits[(opcode & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ',*txt++ = ';',*txt++ = ' ';
        if (lc) *txt++ = 'e',*txt++ = 'n',*txt++ = 'd';
        else *txt++ = 'E',*txt++ = 'N',*txt++ = 'D';
    }
    else if (entry->num_bytes == 7) {
        h = &hexdigits[(opcode & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[1] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[2] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[3] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[4] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[5] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[6] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ',*txt++ = ';',*txt++ = ' ';
        if (lc) *txt++ = 'e',*txt++ = 'n',*txt++ = 'c';
        else *txt++ = 'E',*txt++ = 'N',*txt++ = 'C';
        *txt++ = '=',*txt++ = '$';
        h = &hexdigits[(opcode & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ';
        if (lc) *txt++ = 'x';
        else *txt++ = 'X';
        *txt++ = '=',*txt++ = '$';
        h = &hexdigits[(data[1] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ';
        if (lc) *txt++ = 'y';
        else *txt++ = 'Y';
        *txt++ = '=',*txt++ = '$';
        h = &hexdigits[(data[2] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ';
        if (lc) *txt++ = 't',*txt++ = 'a',*txt++ = 'k',*txt++ = 'e';
        else *txt++ = 'T',*txt++ = 'A',*txt++ = 'K',*txt++ = 'E';
        *txt++ = '=',*txt++ = '$';
        h = &hexdigits[(data[4] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[3] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ';
        if (lc) *txt++ = 'p',*txt++ = 'a',*txt++ = 'i',*txt++ = 'n',*txt++ = 't';
        else *txt++ = 'P',*txt++ = 'A',*txt++ = 'I',*txt++ = 'N',*txt++ = 'T';
        *txt++ = '=',*txt++ = '$';
        h = &hexdigits[(data[6] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        h = &hexdigits[(data[5] & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
    }
    else {
        h = &hexdigits[(opcode & 0xff)*2]; *txt++ = *h++; *txt++ = *h++;
        *txt++ = ' ',*txt++ = ';',*txt++ = ' ',*txt++ = '[';
        if (lc) *txt++ = 'i',*txt++ = 'n',*txt++ = 'c',*txt++ = 'o',*txt++ = 'm',*txt++ = 'p',*txt++ = 'l',*txt++ = 'e',*txt++ = 't',*txt++ = 'e';
        else *txt++ = 'I',*txt++ = 'N',*txt++ = 'C',*txt++ = 'O',*txt++ = 'M',*txt++ = 'P',*txt++ = 'L',*txt++ = 'E',*txt++ = 'T',*txt++ = 'E';
        *txt++ = ']';
    }
    return (int)(txt - first_txt);
}
