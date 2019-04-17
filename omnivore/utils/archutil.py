import re
import collections

import numpy as np

from sawx.persistence import get_template, iter_templates

from ..disassembler.libudis import LabelStorage

import logging
log = logging.getLogger(__name__)



line_re = re.compile("^([a-fA-F0-9]+)\s*([a-zA-Z][a-zA-Z0-9_]*)*\s*([a-zA-Z][a-zA-Z0-9_]*)?\s*(\S*)^")

type_codes = {
    'b': 0, # "byte",
    'w': 1, # "word",
    'l': 3, # "long",
    }

desc_codes = {
    'h': 0x00, # "hex",
    'hex': 0x00,
    'c': 0x10, # "char", "ascii",
    'char': 0x10,
    'ascii': 0x10,
    'a': 0x20, # "atascii",
    'atascii': 0x20,
    'd': 0x30, # "decimal",
    'decimal': 0x30,
    'b': 0x40, # "binary",
    'bin': 0x40,
    'binary': 0x40,
}

SourceLabel = collections.namedtuple('SourceLabel', 'label byte_count item_count type_code desc_code')


class Labels:
    @classmethod
    def from_file(cls, filename):
        text = open(filename).read()
        return cls.from_text(text)

    @classmethod
    def from_text(cls, text):
        m = cls()
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
                read_val, write_val = tokens[1].split("/")
            else:
                read_val = tokens[1]
                write_val = None
            try:
                type_description = tokens[2]
            except IndexError:
                type_description = 'b'
            try:
                desc_code = desc_codes[tokens[3]]
            except IndexError:
                desc_code = desc_codes['hex']
            try:
                m.add(addr, read_val, write_val, type_description, desc_code)
            except RuntimeError:
                log.warning("Invalid type code on line {line_num}: `'{type_code}'")
        return m

    def __init__(self):
        self.labels = LabelStorage()
        self.write_labels = LabelStorage()

    def add(self, addr, r, w, type_description, desc_code):
        type_code = type_codes[type_description[-1]]
        try:
            item_count = int(type_description[:-1])
        except ValueError:
            item_count = 1
        num_bytes = item_count * (type_code + 1)
        label = SourceLabel(r.encode('utf-8'), num_bytes, item_count, type_code, desc_code)
        self.labels[addr] = label
        if w:
            # print(f"found write label {w} at {addr}")
            self.write_labels[addr] = w.encode('utf-8')
            # print(f"stored as: {self.get_name(addr, True)}")

    def get_name(cls, addr, write=False):
        if write:
            if addr in cls.write_labels:
                return cls.write_labels[addr][0].decode('utf-8')
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
        self.write_labels.update(other.write_labels)


machine_labels = {}

def load_memory_map(keyword):
    global machine_labels
    try:
        labels = machine_labels[keyword]
    except KeyError:
        try:
            text = get_template(keyword)
        except OSError as e:
            try:
                text = get_template(keyword + ".labels")
            except OSError as e:
                log.error(f"Couldn't find memory map named '{keyword}'")
                return Labels()
        labels = Labels.from_text(text)
        machine_labels[keyword] = labels
    return labels

available_memory_maps = {}

def calc_available_memory_maps():
    global available_memory_maps
    if not available_memory_maps:
        for template in iter_templates("labels"):
            available_memory_maps[template.keyword] = template
    return available_memory_maps
