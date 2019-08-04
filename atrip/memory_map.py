import os

import numpy as np

import logging
log = logging.getLogger(__name__)


# size_codes and display_codes are combined into a single byte xxxxxxyy
# display_code = x, bytes_per_item = size_code + 1 (1 - 4 bytes per item)

size_codes = {
    'b': 0, # "byte",
    'w': 1, # "word",
    'l': 3, # "long",
    }

display_codes = {
    'h': 0x00, # "hex",
    'he': 0x00,
    'hex': 0x00,
    'c': 0x10, # "char", "ascii",
    'ch': 0x10,
    'cha': 0x10,
    'char': 0x10,
    'as': 0x10,
    'asc': 0x10,
    'asci': 0x10,
    'ascii': 0x10,
    'a': 0x20, # "atascii",
    'at': 0x20,
    'ata': 0x20,
    'atas': 0x20,
    'atasc': 0x20,
    'atasci': 0x20,
    'atascii': 0x20,
    'd': 0x30, # "decimal",
    'de': 0x30,
    'dec': 0x30,
    'deci': 0x30,
    'decim': 0x30,
    'decima': 0x30,
    'decimal': 0x30,
    'b': 0x40, # "binary",
    'bi': 0x40,
    'bin': 0x40,
    'bina': 0x40,
    'binar': 0x40,
    'binary': 0x40,
}


label_description_record_type = np.dtype([  # must match label_description_t
    ('text_length', 'u1'),
    ('num_bytes', 'u1'),
    ('item_count', 'u1'),
    ('type_code', 'u1'),  # size_code | display_code as above
    ('label', 'u1', 12),
    ])

memory_map_record_type = np.dtype([  # must match label_storage_t
    ('flags', 'u2'),
    ('first_addr', 'u2'),
    ('last_addr', 'u2'),
    ('num_labels', 'u2'),
    ('index', 'u2', 256*256),
    ('labels', label_description_record_type, 1024),
    ])


class MemoryMap:
    @classmethod
    def from_file(cls, filename):
        text = open(filename).read()
        return cls.from_text(os.path.basename(filename), text)

    @classmethod
    def from_text(cls, name, text, default_display_key="hex"):
        """Parse lines of text in the format:

            0011 BRKKEY
            0012 RTCLOK        3b
            02a3 TABMAP        15b    binary
            030b DAUX2
            030c TIMER1        w
            0340 IOCB0         16b
            d000 M0PF/HPOSP0

        with 2 required fields and 1 or 2 optional fields, all separated by
        whitespace. The first field is the address, the 2nd is the label, the
        3rd is the data type, and the 4th is the display type. and the
        (optional) 3rd is the size and type of the memory address.

        If the 2nd field contains a "/" character, that will denote a memory
        address that has different uses when read or written to. The read
        address is before the "/", the write address after. Labels may contain
        alphanumeric characters or underscores.

        The optional 3rd field contains the data type; if it is missing, the
        data type is assumed to be a single byte. The data type description is
        one of "b", "w", or "l" (case insensitive), meaning a byte, word (2
        byte), or long-word (4 byte) field. It can be prefixed with a number
        indicating an array of that data type. E.g. "4w" is an array of 4 two-
        byte words.

        The optional 4th field contains a keyword for how the data should be
        presented: "hex", "char", "atascii", "binary", "decimal" or
        abbreviations of those keywords. If missing, the data will be displayed
        in the default type.
        """
        rw = cls(name)
        r = cls(name + " (R)")
        w = cls(name + " (W)")
        try:
            text = text.decode('utf-8')
        except AttributeError as e:
            # already a string!
            pass
        line_num = 0
        for line in text.splitlines():
            line = line.strip()
            line_num += 1
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            line = line.split("#")[0]
            tokens = line.split()
            count = len(tokens)
            if count < 2:
                log.warning(f"Missing label on line {line_num}")
                continue
            try:
                addr = int(tokens[0], 16)
            except ValueError:
                log.warning(f"Invalid hex digits on line {line_num}: '{tokens[0]}'")
                continue
            if "/" in tokens[1]:
                rw_name = None
                r_name, w_name = tokens[1].split("/")
            else:
                rw_name = tokens[1]
                r_name = None
                w_name = None
            try:
                type_key = tokens[2]
            except IndexError:
                type_key = 'b'
            try:
                display_key = tokens[3]
            except IndexError:
                display_key = default_display_key
            try:
                if rw_name is not None:
                    rw.add(addr, rw_name, type_key, display_key)
                if r_name is not None:
                    r.add(addr, r_name, type_key, display_key)
                if w_name is not None:
                    w.add(addr, w_name, type_key, display_key)
            except RuntimeError:
                log.warning("Invalid type code on line {line_num}: `'{type_code}'")
        return rw, r, w

    @classmethod
    def from_list(cls, name, entries, default_display_key="hex"):
        """Parse list of tuples, each tuple in the form of:

            (addr, name[, type_key [, display_key]])

        The addr field must be an integer, name must be a string without a
        slash, and the type and display keys are strings as in the field
        descriptions of `from_text`.
        """
        rw = cls(name)
        line_num = 0
        for tokens in entries:
            count = len(tokens)
            if count < 2:
                log.warning(f"Missing label on line {line_num}")
                continue
            addr = tokens[0]
            rw_name = tokens[1]
            try:
                type_key = tokens[2]
            except IndexError:
                type_key = 'b'
            try:
                display_key = tokens[3]
            except IndexError:
                display_key = default_display_key
            try:
                rw.add(addr, rw_name, type_key, display_key)
            except RuntimeError:
                log.warning("Invalid type code on line {line_num}: `'{type_code}'")
        return rw

    def __init__(self, name):
        self.ui_name = name
        self.labels_raw = np.zeros([memory_map_record_type.itemsize], dtype=np.uint8)
        self.labels = self.labels_raw.view(dtype=memory_map_record_type)
        self.next_index = 1  # index 0 is unused, indicates unused address

    def __str__(self):
        lines = []
        valid = np.where(self.labels['index'][0] > 0)[0]
        for addr in valid:
            index = self.labels['index'][0][addr]
            r = self.labels['labels'][0][index]
            label_size = r['text_length']
            label = "".join(map(chr, r['label'][0:label_size]))
            num_bytes = r['num_bytes']
            item_count = r['item_count']
            type_code = r['type_code']
            lines.append(f"{addr:4x}: {label:8} {num_bytes} {item_count} {type_code}")
        return "\n".join(lines)

    def __contains__(self, addr):
        return self.labels['index'][0][addr] > 0

    def __getitem__(self, addr):
        if isinstance(addr, int):
            index = self.labels['index'][0][addr]
            if index == 0:
                raise KeyError(f"No label at {addr:x}")
            r = self.labels['labels'][0][index]
            label_size = r['text_length']
            label = "".join(map(chr, r['label'][0:label_size]))
            num_bytes = r['num_bytes']
            item_count = r['item_count']
            type_code = r['type_code']
            return (label, num_bytes, item_count, type_code)
        elif isinstance(addr, slice):
            raise TypeError(f"slicing not yet supported")
        else:
            raise TypeError(f"index must be int or slice, not {type(index)}")

    def add(self, addr, name, type_key="b", display_key="hex"):
        # print("PROCESSING", addr, name, type_key, display_key, self.next_index)
        size_code = size_codes[type_key[-1]]
        try:
            item_count = int(type_key[:-1])
        except ValueError:
            item_count = 1
        display_code = display_codes[display_key]
        num_bytes = item_count * (size_code + 1)

        index = self.next_index
        r = self.labels['labels'][0][index]
        name = name.encode('utf-8')
        text_length = len(name)
        r['text_length'] = text_length
        r['num_bytes'] = num_bytes
        r['item_count'] = item_count
        r['type_code'] = size_code | display_code
        r['label'][0:text_length] = [c for c in name]

        self.labels['index'][0][addr] = index

        # long labels take over the next record entries
        if text_length > 12:
            text_length -= 12
            record_count = 1 + (text_length + 15) // 16
        else:
            record_count = 1
        self.next_index += record_count
