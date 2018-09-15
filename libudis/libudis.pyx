from libc.stdio cimport printf
import cython
import numpy as np
cimport numpy as np

from libudis.libudis cimport history_entry_t, parse_func_t, string_func_t

from libudis.declarations cimport find_parse_function, find_string_function

cdef extern:
    string_func_t stringifier_map[]



cdef char *hexdigits_lower = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff"
cdef char *hexdigits_upper = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF"


cdef class ParsedDisassembly:
    cdef history_entry_t *history_entries
    cdef int num_entries
    cdef int entry_size
    cdef public np.ndarray entries
    cdef int entry_index
    cdef int start_pc
    cdef int last_pc
    cdef int current_pc
    cdef public np.ndarray labels
    cdef np.uint16_t *labels_data

    # text representation
    cdef public np.ndarray text_starts
    cdef np.uint16_t *text_starts_data
    cdef public np.ndarray line_lengths
    cdef np.uint16_t *line_lengths_data
    cdef public np.ndarray text_buffer
    cdef char *text_buffer_data
    cdef public int num_text_lines

    def __init__(self, max_entries, start_pc):
        self.num_entries = max_entries
        self.entry_size = 24
        self.entries = np.zeros(max_entries * self.entry_size, dtype=np.uint8)
        self.history_entries = <history_entry_t *>self.entries.data
        self.entry_index = 0
        self.start_pc = start_pc
        self.last_pc = start_pc + self.num_entries
        self.current_pc = start_pc
        self.labels = np.zeros(self.last_pc, dtype=np.uint16)
        self.labels_data = <np.uint16_t *>self.labels.data

        cdef int initial_lines = 100
        self.init_text_lines(initial_lines)

    cdef init_text_lines(self, num_lines):
        self.text_starts = np.zeros(num_lines, dtype=np.uint16)
        self.text_starts_data = <np.uint16_t *>self.text_starts.data
        self.line_lengths = np.zeros(num_lines, dtype=np.uint16)
        self.line_lengths_data = <np.uint16_t *>self.line_lengths.data
        self.text_buffer = np.zeros(num_lines * 256, dtype=np.uint8)
        self.text_buffer_data = <char *>self.text_buffer.data


    cdef parse_next(self, parse_func_t processor, unsigned char *src, int num_bytes):
        cdef history_entry_t *h = &self.history_entries[self.entry_index]
        while self.current_pc < self.last_pc:
            if num_bytes > 0:
                count = processor(h, src, self.current_pc, self.last_pc, self.labels_data)
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
        printf("processor = %lx\n", processor)
        self.parse_next(processor, <unsigned char *>src.data, len(src))

    def stringify(self, int index, int num_lines_requested, mnemonic_lower=True, hex_lower=True):
        cdef history_entry_t *h = &self.history_entries[index]
        cdef int num_text_lines = 0
        cdef char *txt = self.text_buffer_data
        cdef int count
        cdef string_func_t stringifier
        cdef np.uint16_t *starts = self.text_starts_data
        cdef np.uint16_t *lengths = self.line_lengths_data
        cdef np.uint16_t text_index = 0
        cdef int disassembler_type
        cdef int text_case = 1 if mnemonic_lower else 0
        cdef char *hex_case = hexdigits_lower if hex_lower else hexdigits_upper
        while num_lines_requested > 0 and index < self.entry_index:
            disassembler_type = h.disassembler_type
            printf("disassembler: %d\n", disassembler_type)
            stringifier = stringifier_map[disassembler_type]
            printf("stringifier: %lx\n", stringifier)
            for disassembler_type in range(40):
                printf("stringifier[%d] = %lx\n", disassembler_type, stringifier_map[disassembler_type])
            count = stringifier(h, txt, hex_case, text_case)
            starts[index] = text_index
            lengths[index] = count
            text_index += count
            num_text_lines += 1
            txt += count
            num_lines_requested -= 1
            index += 1
            h += 1
        self.num_text_lines = num_text_lines



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
