/* Handwritten parsers */

#include <stdio.h>
#include <string.h>

#include "libudis.h"
#include "stringify_udis_cpu.h"
#include "libdebugger.h"


int print_label_or_addr(int addr, jmp_targets_t *jmp_targets, char *t, char *hexdigits, int zero_page) {
    char *first_t, *h;
    label_info_t *info;
    int index, count;

    first_t = t;
    if (jmp_targets->labels) {
        info = &jmp_targets->labels[(addr & 0xffff)];
        index = info->text_start_index;
    }
    else {
        index = 0;
    }
    if (index) {
        count = info->line_length;
        h = &jmp_targets->text_storage[index];
        while (count > 0) {
            *t++=*h++;
            count--;
        }
    }
    else if (jmp_targets->discovered[addr]) {
        *t++='L';
        h = &hexdigits[(addr >> 8)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(addr & 0xff)*2], *t++=*h++, *t++=*h++;
    }
    else {
        *t++='$';
        if (!zero_page) h = &hexdigits[(addr >> 8)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(addr & 0xff)*2], *t++=*h++, *t++=*h++;
    }
    return (int)(t - first_t);
}


static inline char *STRING(char *t, int lc, char *str) {
    char *c;

    while (c=*str++) {
        *t++=c;
    }
    return t;
}

int stringify_entry_data(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;
    unsigned char *data;

    first_t = t;
    data = entry->instruction;
    if (lc) *t++='.', *t++='b', *t++='y', *t++='t', *t++='e', *t++=' ';
    else *t++='.', *t++='B', *t++='Y', *t++='T', *t++='E', *t++=' ';
    if (entry->flag == FLAG_REPEATED_BYTES) {
        t += sprintf(t, "%d", entry->num_bytes);
        *t++='*';
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    }
    else switch(entry->num_bytes) {
    case 8:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 7:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 6:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 5:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 4:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 3:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    case 2:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    default:
        h = &hexdigits[(*data++ & 0xff)*2], *t++=*h++, *t++=*h++;
    }
    return (int)(t - first_t);
}

int stringify_entry_antic_dl(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
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
            t += print_label_or_addr(entry->target_addr, jmp_targets, t, hexdigits, 0);
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
                    t += print_label_or_addr(entry->target_addr, jmp_targets, t, hexdigits, 0);
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

int stringify_entry_jumpman_harvest(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    unsigned char opcode;
    char *first_t, *h;
    unsigned char *data;

    first_t = t;
    data = entry->instruction;
    opcode = *data;

    if (opcode == 0xff) {
        h = &hexdigits[(opcode & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ',*t++=';',*t++=' ';
        if (lc) *t++='e',*t++='n',*t++='d';
        else *t++='E',*t++='N',*t++='D';
    }
    else if (entry->num_bytes == 7) {
        h = &hexdigits[(opcode & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[1] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[2] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[3] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[4] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[5] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[6] & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ',*t++=';',*t++=' ';
        if (lc) *t++='e',*t++='n',*t++='c';
        else *t++='E',*t++='N',*t++='C';
        *t++='=',*t++='$';
        h = &hexdigits[(opcode & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ';
        if (lc) *t++='x';
        else *t++='X';
        *t++='=',*t++='$';
        h = &hexdigits[(data[1] & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ';
        if (lc) *t++='y';
        else *t++='Y';
        *t++='=',*t++='$';
        h = &hexdigits[(data[2] & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ';
        if (lc) *t++='t',*t++='a',*t++='k',*t++='e';
        else *t++='T',*t++='A',*t++='K',*t++='E';
        *t++='=',*t++='$';
        h = &hexdigits[(data[4] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[3] & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ';
        if (lc) *t++='p',*t++='a',*t++='i',*t++='n',*t++='t';
        else *t++='P',*t++='A',*t++='I',*t++='N',*t++='T';
        *t++='=',*t++='$';
        h = &hexdigits[(data[6] & 0xff)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(data[5] & 0xff)*2], *t++=*h++, *t++=*h++;
    }
    else {
        h = &hexdigits[(opcode & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ',*t++=';',*t++=' ',*t++='[';
        if (lc) *t++='i',*t++='n',*t++='c',*t++='o',*t++='m',*t++='p',*t++='l',*t++='e',*t++='t',*t++='e';
        else *t++='I',*t++='N',*t++='C',*t++='O',*t++='M',*t++='P',*t++='L',*t++='E',*t++='T',*t++='E';
        *t++=']';
    }
    return (int)(t - first_t);
}

int stringify_entry_frame_start(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='S', *t++='t', *t++='a', *t++='r', *t++='t', *t++=' ', *t++='f', *t++='r', *t++='a', *t++='m', *t++='e', *t++=' ';
    t += sprintf(t, "%d", frame->frame_number);
    return (int)(t - first_t);
}

int stringify_entry_frame_end(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='E', *t++='n', *t++='d', *t++=' ', *t++='f', *t++='r', *t++='a', *t++='m', *t++='e', *t++=' ';
    t += sprintf(t, "%d", frame->frame_number);
    *t++=',', *t++=' ', *t++='s', *t++='t', *t++='a', *t++='r', *t++='t', *t++=' ', *t++='f', *t++='r', *t++='a', *t++='m', *t++='e', *t++=' ';
    t += sprintf(t, "%d", frame->frame_number + 1);
    return (int)(t - first_t);
}

int stringify_entry_6502_cpu_registers(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    int val;
    char *first_t, *h;
    history_6502_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    h = &hexdigits[(entry->a & 0xff)*2], *t++=*h++, *t++=*h++;
    *t++=' ';
    h = &hexdigits[(entry->x & 0xff)*2], *t++=*h++, *t++=*h++;
    *t++=' ';
    h = &hexdigits[(entry->y & 0xff)*2], *t++=*h++, *t++=*h++;
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
    h = &hexdigits[(entry->sp & 0xff)*2], *t++=*h++, *t++=*h++;
    return (int)(t - first_t);
}

int stringify_entry_6502_opcode(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;
    history_6502_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    h = &hexdigits[entry->instruction[0]*2], *t++=*h++, *t++=*h++;
    *t++=' ';
    if (entry->num_bytes > 1) {
        h = &hexdigits[entry->instruction[1]*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    else *t++=' ', *t++=' ', *t++=' ';
    if (entry->num_bytes > 2) {
        h = &hexdigits[entry->instruction[2]*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    else *t++=' ', *t++=' ', *t++=' ';
    return (int)(t - first_t);
}

int stringify_entry_6502_history(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;

    first_t = t;
    t += stringify_entry_6502_cpu_registers(entry, t, hexdigits, lc, jmp_targets);
    *t++=' ';
    h = &hexdigits[(entry->pc >> 8)*2], *t++=*h++, *t++=*h++;
    h = &hexdigits[(entry->pc & 0xff)*2], *t++=*h++, *t++=*h++;
    *t++=' ';
    *t++=' ';
    t += stringify_entry_6502_opcode(entry, t, hexdigits, lc, jmp_targets);
    *t++=' ';
    t += stringify_entry_6502(entry, t, hexdigits, lc, jmp_targets);
    return (int)(t - first_t);
}

int stringify_entry_atari800_history(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;
    history_atari800_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    t += stringify_entry_6502_cpu_registers(h_entry, t, hexdigits, lc, jmp_targets);
    *t++=' ';
    // t += sprintf(t, "%3d", (int)entry->antic_ypos | ((entry->antic_xpos & 0x80)<<1));
    // *t++=' ';
    // t += sprintf(t, "%3d", entry->antic_xpos & 0x7f);
    // *t++=' ';
    h = &hexdigits[(entry->pc >> 8)*2], *t++=*h++, *t++=*h++;
    h = &hexdigits[(entry->pc & 0xff)*2], *t++=*h++, *t++=*h++;
    *t++=' ';
    *t++=' ';
    t += stringify_entry_6502_opcode(h_entry, t, hexdigits, lc, jmp_targets);
    *t++=' ';
    t += stringify_entry_6502(h_entry, t, hexdigits, lc, jmp_targets);
    return (int)(t - first_t);
}

int stringify_entry_6502_history_result(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    int val, changed, masked_flag;
    char *first_t, *h;
    history_6502_t *entry = (history_frame_t *)h_entry;

    masked_flag = entry->flag & FLAG_RESULT_MASK;
    first_t = t;
    if (masked_flag == FLAG_LOAD_A_FROM_MEMORY || masked_flag == FLAG_LOAD_X_FROM_MEMORY || masked_flag == FLAG_LOAD_Y_FROM_MEMORY) {
        *t++='$';
        h = &hexdigits[(entry->target_addr >> 8)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(entry->target_addr & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    if (masked_flag == FLAG_BRANCH_TAKEN) {
        *t++='(', *t++='t', *t++='a', *t++='k', *t++='e', *t++='n', *t++=')';
        *t++=' ';
    }
    else if (masked_flag == FLAG_BRANCH_NOT_TAKEN) {
        *t++='(', *t++='n', *t++='o', *t++='t', *t++=' ', *t++='t', *t++='a', *t++='k', *t++='e', *t++='n', *t++=')';
        *t++=' ';
    }
    // else if (masked_flag == FLAG_READ_ONE) {
    //     *t++='R', *t++='e', *t++='a', *t++='d';
    //     *t++=' ';
    // }
    // else if (masked_flag == FLAG_WRITE_ONE) {
    //     *t++='W', *t++='r', *t++='i', *t++='t', *t++='e';
    //     *t++=' ';
    // }
    if (masked_flag == FLAG_STORE_A_IN_MEMORY || masked_flag == FLAG_STORE_X_IN_MEMORY || masked_flag == FLAG_STORE_Y_IN_MEMORY || masked_flag == FLAG_MEMORY_ALTER) {
        *t++='$';
        h = &hexdigits[(entry->target_addr >> 8)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(entry->target_addr & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++='=';
        switch (masked_flag) {
            case FLAG_MEMORY_ALTER:
            val = entry->after1;
            break;
            case FLAG_STORE_X_IN_MEMORY:
            val = entry->x;
            break;
            case FLAG_STORE_Y_IN_MEMORY:
            val = entry->y;
            break;
            default:
            val = entry->a;
        }
        h = &hexdigits[val*2], *t++=*h++, *t++=*h++;
        *t++=' ';
        *t++='(', *t++='w', *t++='a', *t++='s', *t++=' ';
        h = &hexdigits[entry->before1*2], *t++=*h++, *t++=*h++;
        *t++=')';
    }
    else if (masked_flag == FLAG_PEEK_MEMORY) {
        *t++='$';
        h = &hexdigits[(entry->target_addr >> 8)*2], *t++=*h++, *t++=*h++;
        h = &hexdigits[(entry->target_addr & 0xff)*2], *t++=*h++, *t++=*h++;
        *t++='=';
        h = &hexdigits[entry->before1*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    else if (masked_flag == FLAG_REG_A || masked_flag == FLAG_LOAD_A_FROM_MEMORY) {
        *t++='A', *t++='=';
        h = &hexdigits[entry->after1*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    else if (masked_flag == FLAG_REG_X || masked_flag == FLAG_LOAD_X_FROM_MEMORY) {
        *t++='X', *t++='=';
        h = &hexdigits[entry->after1*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    else if (masked_flag == FLAG_REG_Y || masked_flag == FLAG_LOAD_Y_FROM_MEMORY) {
        *t++='Y', *t++='=';
        h = &hexdigits[entry->after1*2], *t++=*h++, *t++=*h++;
        *t++=' ';
    }
    if (entry->flag & FLAG_REG_SR) {
        changed = entry->sr ^ entry->after3;
        val = entry->after3;
        if (changed & 0x80) {*t++='N'; *t++='='; if (val&0x80) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x40) {*t++='V'; *t++='='; if (val&0x40) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x10) {*t++='B'; *t++='='; if (val&0x10) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x8) {*t++='D'; *t++='='; if (val&0x8) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x4) {*t++='I'; *t++='='; if (val&0x4) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x2) {*t++='Z'; *t++='='; if (val&0x2) *t++='1'; else *t++='0'; *t++=' ';}
        if (changed & 0x1) {*t++='C'; *t++='='; if (val&0x1) *t++='1'; else *t++='0'; *t++=' ';}
    }
    return (int)(t - first_t);
}

int stringify_entry_atari800_vbi_start(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='V', *t++='B', *t++='I';
    return (int)(t - first_t);
}

int stringify_entry_atari800_vbi_end(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='V', *t++='B', *t++='I', *t++=' ', *t++='E', *t++='n', *t++='d';
    return (int)(t - first_t);
}

int stringify_entry_atari800_dli_start(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='D', *t++='L', *t++='I';
    return (int)(t - first_t);
}

int stringify_entry_atari800_dli_end(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;
    history_frame_t *frame = (history_frame_t *)entry;

    first_t = t;
    *t++='-', *t++='-', *t++='D', *t++='L', *t++='I', *t++=' ', *t++='E', *t++='n', *t++='d';
    return (int)(t - first_t);
}

int stringify_entry_breakpoint(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;
    history_breakpoint_t *entry = (history_frame_t *)h_entry;

    first_t = t;
    if (entry->breakpoint_type == BREAKPOINT_PAUSE_AT_FRAME_START) {
        t = STRING(t, 0, "<PAUSED>");
    }
    else {
        t = STRING(t, 0, "<BREAKPOINT");
        if (entry->breakpoint_id > 0) {
            t += sprintf(t, " %d", entry->breakpoint_id);
        }
        *t++='>';
        switch (entry->breakpoint_type) {
            case BREAKPOINT_INFINITE_LOOP:
            t = STRING(t, 0, ": infinite loop detected");
            break;

            default:
            break;
        }
    }
    return (int)(t - first_t);
}

int stringify_entry_unknown_disassembler(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t;

    first_t = t;
    *t++='-', *t++='-', *t++='U', *t++='n', *t++='k', *t++='n', *t++='o', *t++='w', *t++='n', *t++=' ', *t++='h', *t++='i', *t++='s', *t++='t', *t++='o', *t++='r', *t++='y',  *t++=' ', *t++='t', *t++='y', *t++='p', *t++='e', *t++=' ';
    t += sprintf(t, "%d", entry->disassembler_type);
    return (int)(t - first_t);
}

int stringify_entry_blank(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    return 0;
}


extern string_func_t stringifier_map[];

int stringify_entry_next_instruction(history_entry_t *h_entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;
    history_breakpoint_t *entry = (history_frame_t *)h_entry;
    string_func_t stringifier = stringifier_map[entry->disassembler_type_cpu];

    return stringifier(entry, t, hexdigits, lc, jmp_targets);
}

int stringify_entry_next_instruction_result(history_entry_t *entry, char *t, char *hexdigits, int lc, jmp_targets_t *jmp_targets) {
    char *first_t, *h;

    return stringify_entry_breakpoint(entry, t, hexdigits, lc, jmp_targets);
}
