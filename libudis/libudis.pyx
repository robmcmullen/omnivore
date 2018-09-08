from __future__ import division
import cython
import numpy as np
cimport numpy as np

from libudis.libudis cimport history_entry_t, parse_func_t

from libudis.disasm_speedups_monolithic cimport find_parse_function


cdef class ParsedDisassembly:
    cdef history_entry_t *history_entries
    cdef int num_entries
    cdef int entry_size
    cdef public np.ndarray entries
    cdef int entry_index
    cdef int start_pc
    cdef int last_pc
    cdef int current_pc
    cdef np.ndarray labels_array
    cdef np.uint16_t *labels

    def __init__(self, max_entries, start_pc):
        self.num_entries = max_entries
        self.entry_size = 12
        self.entries = np.zeros(max_entries * self.entry_size, dtype=np.uint8)
        self.history_entries = <history_entry_t *>self.entries.data
        self.entry_index = 0
        self.start_pc = start_pc
        self.last_pc = start_pc + self.num_entries
        self.current_pc = start_pc
        self.labels_array = np.empty(self.last_pc, dtype=np.uint16)
        self.labels = <np.uint16_t *>self.labels_array.data

    cdef parse_next(self, parse_func_t processor, unsigned char *src, int num_bytes):
        cdef history_entry_t *h = &self.history_entries[self.entry_index]
        while self.current_pc < self.last_pc:
            if num_bytes > 0:
                count = processor(h, src, self.current_pc, self.last_pc, self.labels)
                src += count
                num_bytes -= count
                self.current_pc += count
                self.entry_index += 1
                h += 1
            else:
                break

    def parse_test(self, cpu_type, np.ndarray[np.uint8_t, ndim=1] src):
        cdef parse_func_t processor
        cdef char *c_cpu_type

        cpu_type_bytes = cpu_type.encode('utf-8')
        c_cpu_type = cpu_type_bytes
        processor = find_parse_function(c_cpu_type)
        self.parse_next(processor, <unsigned char *>src.data, len(src))




cdef int data_style = 1

cdef class DisassemblyConfig:
    cdef np.uint8_t c_split_comments[8]
    cdef parse_func_t segment_parsers[8]

    def __init__(self, split_comments=[data_style]):
        for i in range(8):
            self.c_split_comments[i] = 1 if i in split_comments else 0
            self.segment_parsers[i] = NULL

    def register_parser(self, cpu, id):
        cdef char *search_name = cpu
        cdef parse_func_t f
        f = find_parse_function(search_name)
        if f != NULL:
            self.segment_parsers[id] = f

    # cdef fix_offset_labels(self):
    #     # fast loop in C to check for references to addresses that are in the
    #     # middle of an instruction. If found, a label is generated at the first
    #     # byte of the instruction
    #     cdef int pc = self.first_pc
    #     cdef int i = self.num_bytes
    #     cdef np.uint16_t *labels = <np.uint16_t *>self.labels.data
    #     cdef np.uint32_t *index_to_row = <np.uint32_t *>self.index_to_row.data

    #     #print "pc=%04x, last=%04x, i=%04x" % (pc, pc + i, i)
    #     while i > 0:
    #         i -= 1
    #         if labels[pc + i]:
    #             #print "disasm_info: found label %04x, index_to_row[%04x]=%04x" % (pc + i, i, index_to_row[i])
    #             while index_to_row[i - 1] == index_to_row[i] and i > 1:
    #                 i -= 1
    #             #if labels[pc + i] == 0:
    #             #    print "  disasm_info: added label at %04x" % (pc + i)
    #             labels[pc + i] = 1

    # @cython.boundscheck(False)
    # @cython.wraparound(False)
    # def fast_disassemble_segment(self, segment):
    #     cdef int i
    #     cdef np.uint8_t s, s2
    #     cdef int user_bit_mask = 0x7
    #     cdef int comment_bit_mask = 0x40

    #     src_copy = segment.data.tobytes()
    #     cdef np.uint8_t *src = <np.uint8_t *>src_copy
    #     cdef np.ndarray style_copy = segment.get_comment_locations(user=user_bit_mask)
    #     cdef np.uint8_t *c_style = <np.uint8_t *>style_copy.data
    #     cdef num_bytes = len(style_copy)

    #     cdef int origin = segment.origin
    #     cdef int end_addr = origin + len(segment)
    #     cdef int pc = origin

    #     if num_bytes < 1:
    #         return ParsedDisassembly(0, origin)
    #     cdef ParsedDisassembly parsed = ParsedDisassembly(num_bytes, origin)

    #     cdef int first_index = 0
    #     cdef int base_style = c_style[0] & user_bit_mask
    #     cdef int start_index, end_index, chunk_type
        # cdef history_entry_t *h = parsed.history_entries[0]
        # cdef int count
        # cdef char *temp[256]
        # # print "CYTHON FAST_GET_ENTIRE", style_copy
        # ranges = []
        # for i in range(1, num_bytes):
        #     s = style_copy[i]
        #     s2 = s & user_bit_mask
        #     # print "%04x" % i, s, s2,
        #     if s & comment_bit_mask:
        #         if s2 == base_style and not c_split_comments[s2]:
        #             # print "same w/skippable comment"
        #             continue
        #     elif s2 == base_style:
        #         # print "same"
        #         continue

        #     # process chuck here:
        #     start_index = first_index
        #     end_index = i
        #     chunk_type = base_style
        #     print("last\nbreak here -> %x:%x = %s" % (start_index, end_index, chunk_type))
        #     processor = segment_parsers(chunk_type)
        #     h = parsed.history_entries[0]
        #     while start_index < end_index:
        #         count = processor(h, src, temp, )
        #     processor(disassembly_wrapper.metadata_wrapper, segment.rawdata.unindexed_data, pc + start_index, pc + end_index, start_index, disassembly_wrapper.mnemonic_lower , disassembly_wrapper.hex_lower)

        #     first_index = i
        #     base_style = s2

        # # process last chunk
        # start_index = first_index
        # end_index = i + 1
        # chunk_type = base_style
        # processor = disassembly_wrapper.chunk_type_processor.get(chunk_type, disassembly_wrapper.chunk_processor)
        # processor(disassembly_wrapper.metadata_wrapper, segment.rawdata.unindexed_data, pc + start_index, pc + end_index, start_index, disassembly_wrapper.mnemonic_lower , disassembly_wrapper.hex_lower)

        # return DisassemblyInfo(disassembly_wrapper, pc, num_bytes)
