#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include "libemu/disasm.h"
#include "libemu/op_history.h"


int parse_chunk(op_history_t *buf, parse_func_t (*processor)(), int current_pc, int num_bytes, uint8_t *src, uint32_t *order, int index, jmp_targets_t *jmp_targets) {
    op_record_t *first;
    uint32_t *line_index, *byte_index;
    int num_records, count, last_pc;

    first = (op_record_t *)buf + OP_HISTORY_T_SIZE + buf->num_records;
    line_index = (uint32_t *)buf + OP_HISTORY_T_SIZE + buf->max_records + buf->num_line_to_record;
    byte_index = (uint32_t *)((op_record_t *)buf) + OP_HISTORY_T_SIZE + buf->max_records + buf->max_line_to_record + buf->num_byte_to_line;
    last_pc = current_pc + num_bytes;

    while ((current_pc < last_pc) && (num_bytes > 0)) {
        num_records = processor(first, src, order, current_pc, last_pc, jmp_targets);
        count = first->num;
        order += count;
        num_bytes -= count;
        current_pc += count;
        while (count-- > 0) {
            *byte_index++ = buf->num_line_to_record;
            buf->num_byte_to_line++;
        }
        *line_index++ = buf->num_records;
        buf->num_line_to_record++;
        buf->num_records += num_records;
        first += num_records;
    }
    return current_pc;
}

/* fill an op_history_t buffer with disassembly based on a atrip segment:
 * a block of data with a separate array defining the order. The segment also
 * has separate arrays for the styling (a bit field) and the disassembler type,
 * each of which follows the same order as the data. The split_comments
 * parameter is a 256 byte array denoting if a comment occurring in the middle
 * of a run of a particular disassembler will force a new line.
 */
int disassemble(op_history_t *buf, int origin, int num_bytes, uint8_t *src, uint8_t *style, uint8_t *disasm_type, uint32_t *order, uint8_t *split_comments, jmp_targets_t *jmp_targets) {
    parse_func_t (*processor)();
    int i, index, first_index, count;
    uint8_t s, t;
    uint8_t current_disasm_type = disasm_type[order[0]];

    // check output storage size
    if (buf->max_records - buf->num_records < num_bytes * 10) {
        printf("ERROR: record array size (%d) not large enough for expected size (%d)\n", buf->max_records - buf->num_records, num_bytes * 10);
        return -1;
    }
    if (buf->max_line_to_record - buf->num_line_to_record < num_bytes + 256) {
        printf("ERROR: line storage array size (%d) not large enough for expected size (%d)\n", buf->max_line_to_record - buf->num_line_to_record, num_bytes + 256);
        return -1;
    }
    if (buf->max_byte_to_line - buf->num_byte_to_line < num_bytes + 256) {
        printf("ERROR: byte index array size (%d) not large enough for expected size (%d)\n", buf->max_byte_to_line - buf->num_byte_to_line, num_bytes + 256);
        return -1;
    }

    first_index = 0;
    for (index=0; index<num_bytes; index++) {
        i = order[index];
        s = style[i];
        t = disasm_type[i];

        if (t == current_disasm_type) {
            if ((s & COMMENT_BIT_MASK) && split_comments[t]) {
                ; /* fallthrough, process as separate chunk */
            }
            else {
                continue;
            }
        }

        count = index - first_index;
        printf("chunk here -> %x:%x = %d\n", first_index, index, current_disasm_type);
        processor = (parse_func_t *)(parser_map[current_disasm_type]);
        origin = parse_chunk(buf, processor, origin, count, src, &order[index], first_index, jmp_targets);
        first_index = index;
        current_disasm_type = t;
    }

    /* may be one more chunk at the end */
    count = index - first_index;
    printf("final chunk here -> %x:%x = %d\n", first_index, index, current_disasm_type);
    processor = (parse_func_t *)(parser_map[current_disasm_type]);
    origin = parse_chunk(buf, processor, origin, count, src, &order[index], first_index, jmp_targets);


    // parsed.fix_offset_labels()
    // print("finished offset label generation")
    return num_bytes;
}
