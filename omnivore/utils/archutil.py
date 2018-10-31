import re
import collections

import numpy as np

from omnivore_framework.templates import get_template

from ..disassembler.libudis import LabelStorage

import logging
log = logging.getLogger(__name__)



line_re = re.compile("^([a-fA-F0-9]+)\s*([a-zA-Z][a-zA-Z0-9_]*)*\s*([a-zA-Z][a-zA-Z0-9_]*)?\s*(\S*)^")

size_of_type_codes = {
    ord('b'): 1, # "byte",
    ord('w'): 2, # "word",
    ord('l'): 4, # "long",
    }

desc_codes = {
    'c': 1, # "char",
    'a': 2, # "atascii",
}

SourceLabel = collections.namedtuple('SourceLabel', 'label byte_count item_count type_code')


class Labels:
    @classmethod
    def from_text(cls, text):
        m = cls()
        line_num = 0
        for line in text.splitlines():
            line = line.strip()
            line_num += 1
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            line = line.split("#")[0]
            tokens = line.encode('utf-8').split()
            count = len(tokens)
            if count < 2:
                log.warning(f"Missing label on line {line_num}")
                continue
            try:
                addr = int(tokens[0], 16)
            except ValueError:
                log.warning(f"Invalid hex digits on line {line_num}: '{tokens[0]}'")
                continue
            if b"/" in tokens[1]:
                read_val, write_val = tokens[1].split(b"/")
            else:
                read_val = tokens[1]
                write_val = None
            try:
                type_description = tokens[2]
            except IndexError:
                type_description = b'b'
            try:
                m.add(addr, read_val, write_val, type_description)
            except RuntimeError:
                log.warning("Invalid type code on line {line_num}: `'{type_code}'")
        return m

    def __init__(self):
        self.labels = LabelStorage()
        self.write_labels = LabelStorage()

    def add(self, addr, r, w, type_description):
        print(type_description, type(type_description))
        type_code = int(type_description[-1])
        try:
            item_count = int(type_description[:-1])
        except ValueError:
            item_count = 1
        num_bytes = item_count * size_of_type_codes[type_code]
        label = SourceLabel(r, num_bytes, item_count, type_code)
        self.labels[addr] = label
        if w:
            self.write_labels[addr] = w

    def get_name(cls, addr, write=False):
        if write:
            if addr in cls.write_labels:
                return cls.write_labels[addr].decode('utf-8')
        if addr in cls.labels:
            return cls.labels[addr][0].decode('utf-8')
        return ""

    def __contains__(self, addr):
        return addr in self.labels

    def __str__(self):
        lines = []
        a = sorted(set(self.labels.keys()).union(set(self.write_labels.keys())))
        for addr in a:
            try:
                s = self.labels[addr]
            except KeyError:
                s = SourceLabel(addr, "", 1, "b")
            r = s[0].decode('utf-8')
            w = self.get_name(addr, True)
            if r == w:
                w = ""
            lines.append(f"{addr:4x}: {r:8} {w:8} {s[3]}")
        return "\n".join(lines)

    def update(self, other):
        self.labels.update(other.labels)
        # self.write_labels.update(other.write_labels)


def load_memory_map(keyword):
    try:
        text = get_template(keyword)
    except IOError as e:
        log.error(f"Couldn't find memory map named '{keyword}'")
        return SourceLabel()
    m = SourceLabel.from_text(text)
    return m
