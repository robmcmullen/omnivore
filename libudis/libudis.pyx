# cython: language_level=3
from libc.stdio cimport printf
from libc.string cimport strstr, strcasestr
import cython
import numpy as np
cimport numpy as np

from libudis.libudis cimport history_entry_t, emulator_history_t, parse_func_t, string_func_t, jmp_targets_t, label_info_t

from omnivore.disassembler.dtypes import HISTORY_ENTRY_DTYPE

cdef extern:
    parse_func_t parser_map[]
    string_func_t stringifier_map[]
    parse_func_t find_parse_function(char *)
    string_func_t find_string_function(char *)


cdef char *hexdigits_lower = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff"
cdef char *hexdigits_upper = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF"


cdef class TextStorage:
    cdef int max_lines
    cdef public int num_lines
    cdef public np.ndarray label_info
    cdef label_info_t *label_info_data
    cdef public np.ndarray text_buffer
    cdef char *text_buffer_data
    cdef int text_buffer_size
    cdef char *text_ptr
    cdef np.uint32_t text_index

    def __init__(self, max_lines, buffer_size=None):
        if buffer_size is None:
            buffer_size = max_lines * 64
        self.alloc_arrays(max_lines, buffer_size)
        self.clear()

    def alloc_arrays(self, max_lines, buffer_size):
        self.label_info = np.zeros(max_lines * sizeof(label_info_t), dtype=np.uint8)
        self.label_info_data = <label_info_t *>self.label_info.data
        self.text_buffer_size = buffer_size
        self.text_buffer = np.zeros(buffer_size, dtype=np.uint8)
        self.text_buffer_data = <char *>self.text_buffer.data
        self.max_lines = max_lines

    def __len__(self):
        return self.num_lines

    def __contains__(self, index):
        return index > 0 and index < self.num_lines

    def __getitem__(self, index):
        cdef label_info_t *info
        cdef int i, start, count

        if isinstance(index, slice):
            lines = []
            for i in range(*index.indices(len(self))):
                info = &self.label_info_data[i]
                start = info.text_start_index
                count = info.line_length
                lines.append(self.text_buffer[start:start + count].tostring())
            return lines
        elif isinstance(index, int):
            i = index
            info = &self.label_info_data[i]
            start = info.text_start_index
            count = info.line_length
            return self.text_buffer[start:start + count].tostring()
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __iter__(self):
        cdef label_info_t *info
        cdef int i, start, count

        for i in range(self.num_lines):
            info = &self.label_info_data[i]
            start = info.text_start_index
            count = info.line_length
            yield self.text_buffer[start:start + count].tostring()

    cdef clear(self):
        self.num_lines = 0
        self.text_index = 0
        self.text_ptr = self.text_buffer_data

    cdef store(self, int count):
        cdef label_info_t *info
        cdef int i

        i = self.num_lines
        if i >= self.max_lines:
            print(f"CYTHON ERROR! Text buffer line count {self.max_lines} exceeded in TextStorage, attempted to save {i} lines")
        info = &self.label_info_data[i]
        info.line_length = count
        info.text_start_index = self.text_index
        self.text_index += count
        self.text_ptr += count
        self.num_lines += 1
        if self.text_index >= self.text_buffer_size:
            print(f"CYTHON ERROR! Text buffer size {self.text_buffer_size} exceeded in TextStorage, attempted to save {self.text_index} bytes")
        #print(f"stored line {i}, max={self.max_lines}, storage: index={self.text_index}, max={self.text_buffer_size}")

    def get_label_data_addr(self):
        return long(<long>&self.label_info_data[0])

    def get_text_storage_addr(self):
        return long(<long>&self.text_buffer_data[0])


cdef class LabelStorage(TextStorage):
    def __init__(self):
        TextStorage.__init__(self, 256*256, 256*256)

    def __contains__(self, index):
        cdef label_info_t *info
        cdef int i = index

        info = &self.label_info_data[i]
        return info.text_start_index > 0

    def __getitem__(self, index):
        cdef label_info_t *info
        cdef int i, start, count
        cdef np.uint8_t num_bytes, item_count, type_code

        if isinstance(index, int):
            i = index
            info = &self.label_info_data[i]
            start = info.text_start_index
            count = info.line_length
            return (self.text_buffer[start:start + count].tostring(), info.num_bytes, info.item_count, info.type_code)
        elif isinstance(index, slice):
            raise TypeError(f"slicing not yet supported")
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __iter__(self):
        cdef int i
        cdef label_info_t *info
        info = &self.label_info_data[0]
        for i in range(self.max_lines):
            if info.text_start_index > 0:
                yield self[i]
            info += 1

    def __setitem__(self, index, value):
        cdef label_info_t *info
        cdef int i, start, count
        cdef np.uint8_t num_bytes, item_count, type_code

        if isinstance(index, int):
            i = index
            start = self.text_index
            try:
                if isinstance(value, bytes):
                    raise ValueError
                try:
                    value, num_bytes, item_count, type_code, desc_code = value
                except ValueError:
                    value, num_bytes, item_count, type_code = value
                    desc_code = type_code
            except ValueError:
                num_bytes = 1
                item_count = 1
                type_code = 0
                desc_code = 0
            count = len(value)
            if i >= self.max_lines:
                print(f"CYTHON ERROR! Text buffer line count {self.max_lines} exceeded in LabelStorage, attempted to save {i} lines")
            if start + count >= self.text_buffer_size:
                print(f"CYTHON ERROR! Text buffer size {self.text_buffer_size} exceeded in LabelStorage, attempted to save {start + count} bytes")
            info = &self.label_info_data[i]
            info.line_length = count
            info.text_start_index = self.text_index
            info.num_bytes = num_bytes
            info.item_count = item_count
            info.type_code = (type_code & 0x03) | desc_code
            self.text_index += count
            self.num_lines += 1
            # print("assigning value", value, type(value), hex(<long>info))
            for i in range(count):
                self.text_buffer[start] = value[i]
                start += 1
        elif isinstance(index, slice):
            raise TypeError(f"setting labels via slices not yet supported")
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __delitem__(self, index):
        cdef label_info_t *info
        cdef int i

        if isinstance(index, int):
            i = index
            info = &self.label_info_data[i]
            info.text_start_index = 0
            self.num_lines -= 1
        elif isinstance(index, slice):
            raise TypeError(f"deleting labels via slices not yet supported")
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def print_all(self):
        cdef label_info_t *info
        cdef int i, start, count

        info = &self.label_info_data[0]
        print("print_all", self, self.label_info.data, hex(<long>info), self.label_info)
        for i in range(min(5, self.max_lines)):
            start = info.text_start_index
            if start > 0:
                count = info.line_length
                print("entry:", i, start, count, info.num_bytes, info.item_count, info.type_code, self.text_buffer[start:start + count].tostring())
            info += 1
        if self.num_lines - 5 > 0:
            print("...", self.num_lines - 5, "more")
        print("total = ", self.num_lines)

    def keys(self):
        cdef label_info_t *info
        cdef int i

        addresses = []
        info = &self.label_info_data[0]
        for i in range(self.max_lines):
            if info.text_start_index > 0:
                addresses.append(i)
            info += 1
        return addresses

    def update(self, other):
        cdef label_info_t *info
        cdef int i, start, count
        cdef long addr

        addr = other.get_label_data_addr()
        info = <label_info_t *>addr
        # print(other, other.label_info.data, hex(<long>info), other.label_info)
        for i in range(self.max_lines):
            start = info.text_start_index
            if start > 0:
                count = info.line_length
                # print("found other", i, start, count, info.num_bytes, info.item_count, info.type_code, other.text_buffer[start:start + count])
                self[i] = (other.text_buffer[start:start + count], info.num_bytes, info.item_count, info.type_code)
            info += 1

    cdef clear(self):
        cdef label_info_t *info
        cdef int i

        info = &self.label_info_data[0]
        for i in range(self.max_lines):
            info.text_start_index = 0
            info += 1
        self.num_lines = 0
        self.text_index = 1  # special case: no string if text_starts[x] == 0
        self.text_ptr = self.text_buffer_data


cdef class StringifiedDisassembly:
    cdef public int origin
    cdef public int last_pc
    cdef public int start_index
    cdef public np.ndarray jmp_targets
    cdef jmp_targets_t *jmp_targets_data

    cdef public TextStorage disasm_text

    # internals
    cdef int mnemonic_case
    cdef char *hex_case

    def __init__(self, start_index, max_lines, jmp_targets, labels=None, mnemonic_lower=True, hex_lower=True):
        cdef label_info_t *info
        cdef char *text
        cdef long addr

        self.start_index = start_index
        self.disasm_text = TextStorage(max_lines)
        self.mnemonic_case = 1 if mnemonic_lower else 0
        self.hex_case = hexdigits_lower if hex_lower else hexdigits_upper
        self.jmp_targets = jmp_targets
        self.jmp_targets_data = <jmp_targets_t *>self.jmp_targets.data

        if labels is not None:
            addr = labels.get_text_storage_addr()
            text = <char *>addr
            self.jmp_targets_data.text_storage = text

            addr = labels.get_label_data_addr()
            info = <label_info_t *>addr
            self.jmp_targets_data.labels = info
        else:
            self.jmp_targets_data.text_storage = <char *>0
            self.jmp_targets_data.labels = <label_info_t *>0

        self.clear()
        # for disassembler_type in range(40):
        #     printf("stringifier[%d] = %lx\n", disassembler_type, stringifier_map[disassembler_type])

    def __len__(self):
        return self.disasm_text.num_lines

    def __getitem__(self, index):
        if isinstance(index, slice):
            lines = []
            for i in range(*index.indices(len(self))):
                lines.append(self.disasm_text[i])
            return lines
        elif isinstance(index, int):
            return self.disasm_text[index]

        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __iter__(self):
        for i in range(len(self)):
            yield self.disasm_text[i]

    cdef clear(self):
        self.origin = 0
        self.last_pc = 0
        self.disasm_text.clear()

    cdef parse_history_entries(self, history_entry_t *h, int num_entries):
        if num_entries > self.disasm_text.max_lines:
            num_entries = self.disasm_text.max_lines
        cdef int count
        cdef string_func_t stringifier

        self.disasm_text.clear()
        while num_entries > 0:
            stringifier = stringifier_map[h.disassembler_type]
            # printf("disassembler: %d, stringifier: %lx\n", h.disassembler_type, stringifier)
            count = stringifier(h, self.disasm_text.text_ptr, self.hex_case, self.mnemonic_case, self.jmp_targets_data)
            self.disasm_text.store(count)
            num_entries -= 1
            h += 1

    cdef search(self, history_entry_t *h, int num_entries, search_bytes, int match_case):
        cdef char *search = search_bytes
        cdef char *text = self.disasm_text.text_ptr
        cdef char *found
        cdef int pc = h.pc
        matches = []
        # printf("Searching for: %s in %d lines\n", search, num_entries)
        while num_entries > 0:
            stringifier = stringifier_map[h.disassembler_type]
            count = stringifier(h, text, self.hex_case, self.mnemonic_case, self.jmp_targets_data)
            text[count] = 0

            if match_case:
                found = strstr(text, search)
            else:
                found = strcasestr(text, search)
            if found:
                matches.append((h.pc - pc, h.pc - pc + h.num_bytes))
                # printf("disassembler: %d, remaining: %d, line: %s, found: %s\n", h.disassembler_type, num_entries, text, found)
            num_entries -= 1
            h += 1

        # printf("Searched for: %s, found %d matches\n", search, len(matches))
        return matches



cdef class ParsedDisassembly:
    cdef history_entry_t *history_entries
    cdef public int max_entries
    cdef int entry_size
    cdef public np.ndarray raw_entries
    cdef int num_entries
    cdef public int origin
    cdef int last_pc
    cdef int current_pc
    cdef public np.ndarray jmp_targets
    cdef jmp_targets_t *jmp_targets_data
    cdef public int num_bytes
    cdef np.uint32_t *index_to_row_data
    cdef public np.ndarray index_to_row
    cdef int index_index
    cdef int max_text_lines

    def __init__(self, max_entries, origin, num_bytes):
        self.max_entries = max_entries
        self.entry_size = sizeof(history_entry_t)
        self.raw_entries = np.zeros((max_entries + 1) * self.entry_size, dtype=np.uint8)
        self.history_entries = <history_entry_t *>self.raw_entries.data
        self.num_entries = 0
        self.origin = origin
        self.last_pc = origin
        self.current_pc = origin
        self.jmp_targets = np.zeros(sizeof(jmp_targets_t), dtype=np.uint8)
        self.jmp_targets_data = <jmp_targets_t *>self.jmp_targets.data

        self.num_bytes = num_bytes
        self.index_to_row = np.zeros(num_bytes + 1, dtype=np.uint32)
        self.index_to_row_data = <np.uint32_t *>self.index_to_row.data
        self.index_index = 0

        self.max_text_lines = 256

    def __len__(self):
        return self.num_entries

    cdef parse_next(self, parse_func_t processor, unsigned char *src, int num_bytes):
        cdef history_entry_t *h = &self.history_entries[self.num_entries]
        cdef int last_pc = self.current_pc + num_bytes
        cdef np.uint32_t *index_list = self.index_to_row_data
        cdef int i
        while self.current_pc < last_pc and self.num_entries < self.max_entries:
            if num_bytes > 0:
                count = processor(h, src, self.current_pc, last_pc, self.jmp_targets_data)
                src += count
                num_bytes -= count
                self.current_pc += count
                for i in range(count):
                    index_list[self.index_index] = self.num_entries
                    self.index_index += 1
                self.num_entries += 1
                h += 1
            else:
                break
        if self.num_entries >= self.max_entries:
            print(f"CYTHON ERROR! ParsedDisassembly disassembly entries {self.max_entries} exceeded, attempted to save {self.num_entries}")
        if self.index_index > self.num_bytes:
            print(f"CYTHON ERROR! ParsedDisassembly index_to_row entries {self.num_bytes} exceeded, attempted to save {self.index_index}")

    cdef fix_offset_labels(self):
        # fast loop in C to check for references to addresses that are in the
        # middle of an instruction. If found, a discovered address is generated
        # at the first byte of the instruction
        cdef int pc = self.origin
        cdef int i = self.num_bytes
        cdef np.uint8_t *jmp_target = <np.uint8_t *>self.jmp_targets_data
        cdef np.uint32_t *index_to_row = self.index_to_row_data
        cdef np.uint8_t disassembler_type

        #print "pc=%04x, last=%04x, i=%04x" % (pc, pc + i, i)
        while i > 0:
            i -= 1
            old_label = jmp_target[(pc + i) & 0xffff]
            if old_label:
                #print "disasm_info: found label %04x, index_to_row[%04x]=%04x" % (pc + i, i, index_to_row[i])
                while index_to_row[i - 1] == index_to_row[i] and i > 1:
                    i -= 1
                #if labels[pc + i] == 0:
                #    print "  disasm_info: added label at %04x" % (pc + i)
                jmp_target[(pc + i) & 0xffff] = old_label

    def parse_test(self, np.uint8_t disasm_type, np.ndarray[np.uint8_t, ndim=1] src):
        cdef parse_func_t processor

        processor = parser_map[disasm_type]
        # printf("processor = %lx\n", processor)
        self.parse_next(processor, <unsigned char *>src.data, len(src))

    def stringify(self, int index, int num_lines_requested, labels=None, mnemonic_lower=True, hex_lower=True):
        cdef history_entry_t *h = &self.history_entries[index]
        output = StringifiedDisassembly(index, num_lines_requested, self.jmp_targets, labels, mnemonic_lower, hex_lower)
        output.parse_history_entries(h, num_lines_requested)
        return output

    def search(self, search_bytes, match_case=False, labels=None):
        cdef history_entry_t *h = &self.history_entries[0]
        output = StringifiedDisassembly(0, 100, self.jmp_targets, labels, not match_case, not match_case)
        return output.search(h, self.num_entries, search_bytes, match_case)


cdef int data_style = 0

cdef class DisassemblyConfig:
    cdef np.uint8_t c_split_comments[256]
    cdef parse_func_t segment_parsers[256]
    cdef np.uint8_t default_disasm_type

    def __init__(self, def_disasm_type=0, split_comments=[data_style]):
        cdef int i
        for i in range(256):
            self.c_split_comments[i] = 1 if i in split_comments else 0
        self.default_disasm_type = def_disasm_type

    def get_parser(self, num_entries, origin, num_bytes):
        # has to be a python function because it can be overridden in
        # subclasses
        return ParsedDisassembly(num_entries, origin, num_bytes)

    @cython.boundscheck(False)
    @cython.wraparound(False)
    def parse(self, segment, num_entries):
        cdef np.uint8_t s, t
        cdef int comment_bit_mask = 0x40

        src_copy = segment.data.tobytes()
        cdef np.uint8_t *src = <np.uint8_t *>src_copy
        style_copy = segment.style.tobytes()
        cdef np.uint8_t *c_style = <np.uint8_t *>style_copy
        disasm_type_copy = segment.disasm_type.tobytes()
        cdef np.uint8_t *c_disasm_type = <np.uint8_t *>disasm_type_copy
        cdef int num_bytes = len(src_copy)

        cdef int origin = segment.origin
        cdef int end_addr = origin + len(segment)
        cdef int pc = origin

        if num_bytes < 1:
            return self.get_parser(0, origin, 0)
        cdef ParsedDisassembly parsed = self.get_parser(num_entries, origin, num_bytes)

        cdef int first_index = 0
        cdef np.uint8_t current_disasm_type = c_disasm_type[0]
        cdef int start_index
        cdef int end_index = 0
        cdef int count
        # print "CYTHON FAST_GET_ENTIRE", style_copy
        for end_index in range(1, num_bytes):
            s = c_style[end_index]
            t = c_disasm_type[end_index]
            if t > 127:
                t = self.default_disasm_type
            # print "%04x" % i, s, s2,
            if s & comment_bit_mask:
                if t == current_disasm_type and not self.c_split_comments[t]:
                    # print("same w/skippable comment")
                    continue
            elif t == current_disasm_type:
                # print "same"
                continue

            # process chuck here:
            start_index = first_index
            count = end_index - start_index
            # print("break here -> %x:%x = %s" % (start_index, end_index, current_disasm_type))
            processor = parser_map[current_disasm_type]
            parsed.parse_next(processor, src, count)
            src += count
            first_index = end_index
            current_disasm_type = t

        # process last chunk
        start_index = first_index
        end_index += 1  # i is last byte tested, need +1 to include it in the range
        count = end_index - start_index
        # print("final break here -> %x:%x = %s, count=%x" % (start_index, end_index, current_disasm_type, num_bytes))
        processor = parser_map[current_disasm_type]
        parsed.parse_next(processor, src, count)

        parsed.fix_offset_labels()
        # print("finished offset label generation")
        return parsed


cdef class StringifiedHistory:
    cdef public int origin
    cdef public int last_pc
    cdef public int start_index
    cdef public np.ndarray jmp_targets
    cdef jmp_targets_t *jmp_targets_data

    cdef public TextStorage history_text
    cdef public TextStorage result_text

    # internals
    cdef int mnemonic_case
    cdef char *hex_case

    def __init__(self, max_lines, labels=None, mnemonic_lower=True, hex_lower=True):
        cdef long addr

        self.history_text = TextStorage(max_lines)
        self.result_text = TextStorage(max_lines)
        self.mnemonic_case = 1 if mnemonic_lower else 0
        self.hex_case = hexdigits_lower if hex_lower else hexdigits_upper
        self.clear()
        self.jmp_targets = np.zeros(sizeof(jmp_targets_t), dtype=np.uint8)
        self.jmp_targets_data = <jmp_targets_t *>self.jmp_targets.data

        if labels is not None:
            addr = labels.get_text_storage_addr()
            text = <char *>addr
            self.jmp_targets_data.text_storage = text

            addr = labels.get_label_data_addr()
            info = <label_info_t *>addr
            self.jmp_targets_data.labels = info
        else:
            self.jmp_targets_data.text_storage = <char *>0
            self.jmp_targets_data.labels = <label_info_t *>0

    def __len__(self):
        return self.history_text.num_lines

    def __getitem__(self, index):
        if isinstance(index, slice):
            lines = []
            for i in range(*index.indices(len(self))):
                lines.append((self.history_text[i], self.result_text[i]
))
            return lines
        elif isinstance(index, int):
            return self.history_text[index], self.result_text[index]

        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __iter__(self):
        for i in range(len(self)):
            yield self.history_text[i], self.result_text[i]

    cdef clear(self):
        self.history_text.clear()
        self.result_text.clear()

    cdef parse_history_entries(self, emulator_history_t *history, int index, int num_entries):
        if num_entries > self.history_text.max_lines:
            num_entries = self.history_text.max_lines
        cdef int count
        cdef int disassembler_type
        cdef string_func_t stringifier
        cdef history_entry_t *h

        self.clear()
        while num_entries > 0:
            h = &history.entries[index]
            disassembler_type = h.disassembler_type
            stringifier = stringifier_map[disassembler_type]
            # printf("disassembler: %d, stringifier: %lx\n", h.disassembler_type, stringifier)
            count = stringifier(h, self.history_text.text_ptr, self.hex_case, self.mnemonic_case, self.jmp_targets_data)
            self.history_text.store(count)

            if disassembler_type < 192:
                stringifier = stringifier_map[h.disassembler_type + 1]
            # printf("disassembler: %d, stringifier: %lx\n", h.disassembler_type, stringifier)
                count = stringifier(h, self.result_text.text_ptr, self.hex_case, self.mnemonic_case, self.jmp_targets_data)
            else:
                count = 0
            self.result_text.store(count)

            num_entries -= 1
            index += 1
            if index >= history.num_allocated_entries:
                index = 0

cdef class HistoryStorage:
    cdef public np.ndarray history_array
    cdef emulator_history_t *history
    cdef public np.ndarray entries

    def __init__(self, num_entries):
        self.history_array = np.zeros(sizeof(emulator_history_t), dtype=np.uint8)
        self.history = <emulator_history_t *>self.history_array.data
        # printf("libudis: __init__: history_storage: %lx\n", <int>self.history)
        self.history.num_allocated_entries = num_entries
        self.entries = np.zeros(num_entries, dtype=HISTORY_ENTRY_DTYPE)
        self.history.entries = <history_entry_t *>self.entries.data
        self.clear()

    def __len__(self):
        return self.history.num_entries

    def __getitem__(self, index):
        cdef int wrapped

        if isinstance(index, slice):
            lines = []
            for i in range(*index.indices(len(self))):
                wrapped = (i + self.history.first_entry_index) % self.history.num_allocated_entries
                lines.append(self.entries[wrapped])
            return lines
        elif isinstance(index, int):
            wrapped = (index + self.history.first_entry_index) % self.history.num_allocated_entries
            return self.entries[wrapped]
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def __iter__(self):
        for i in range(self.num_lines):
            yield self.entries[i]

    @property
    def first_entry_index(self):
        return self.history.first_entry_index

    @property
    def latest_entry_index(self):
        return self.history.latest_entry_index

    @property
    def next_entry_index(self):
        cdef np.int32_t last = self.history.latest_entry_index
        cdef np.int32_t mod = self.history.num_allocated_entries
        return ((last + 1) % mod)

    @property
    def cumulative_count(self):
        return self.history.cumulative_count

    cdef clear(self):
        self.history.first_entry_index = 0
        self.history.latest_entry_index = -1
        self.history.num_entries = 0
        self.history.cumulative_count = 0

    def summary(self):
        start = self.history.first_entry_index
        last = self.history.latest_entry_index
        mod = self.history.num_allocated_entries
        num = self.history.num_entries
        print(f"number of entries: {mod}, used: {num}, cumulative {self.history.cumulative_count}")
        print(f"start of ring: {start}, latest: {last}")
        print("summary:", self)
        printf("libudis: history_storage: %lx\n", <long int>self.history)

    def debug_range(self, from_index):
        last = self.history.latest_entry_index
        mod = self.history.num_allocated_entries
        num = self.history.num_entries
        print(f"{mod} entries; {from_index} -> {last % mod}")
        cdef i = from_index % mod
        print(f"{i}: {self.entries[i]}")
        i = (from_index+1) % mod
        print(f"{i}: {self.entries[i]}")
        print("  ...")
        i = (last - 1) % mod
        print(f"{i}: {self.entries[i]}")
        i = last % mod
        print(f"{i}: {self.entries[i]}")

    def stringify(self, int index, int num_lines_requested, labels=None, mnemonic_lower=True, hex_lower=True):
        output = StringifiedHistory(num_lines_requested, labels, mnemonic_lower, hex_lower)
        index = (self.history.first_entry_index + index) % self.history.num_allocated_entries
        output.parse_history_entries(self.history, index, num_lines_requested)
        return output
