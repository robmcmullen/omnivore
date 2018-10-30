import re
import collections

import numpy as np

from omnivore_framework.templates import get_template

import logging
log = logging.getLogger(__name__)



line_re = re.compile("^([a-fA-F0-9]+)\s*([a-zA-Z][a-zA-Z0-9_]*)*\s*([a-zA-Z][a-zA-Z0-9_]*)?\s*(\S*)^")

size_codes = {
    'b': 1, # "byte",
    'w': 2, # "word",
    'l': 4, # "long",
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
                type_code = tokens[2]
            except IndexError:
                type_code = 'b'
            try:
                m.add(addr, read_val, write_val, type_code)
            except RuntimeError:
                log.warning("Invalid type code on line {line_num}: `'{type_code}'")
        return m

    def __init__(self):
        self.labels = {}
        self.write_labels = {}

    def add(self, addr, r, w, type_code):
        label = SourceLabel(r, 1, 1, type_code)
        self.labels[addr] = label
        if w:
            self.write_labels[addr] = w

    def get_name(cls, addr, write=False):
        if write:
            if addr in cls.write_labels:
                return cls.write_labels[addr]
        if addr in cls.labels:
            return cls.labels[addr][0]
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
            r = s[0]
            w = self.get_name(addr, True)
            if r == w:
                w = ""
            lines.append(f"{addr:4x}: {r:8} {w:8} {s.type_code}")
        return "\n".join(lines)

    def update(self, other):
        self.labels.update(other.labels)
        self.write_labels.update(other.write_labels)


def load_memory_map(keyword):
    try:
        text = get_template(keyword)
    except IOError as e:
        log.error(f"Couldn't find memory map named '{keyword}'")
        return SourceLabel()
    m = SourceLabel.from_text(text)
    return m


if __name__ == "__main__":
    filename = "../templates/atari800.labels"
    text = open(filename).read()
    labels1 = Labels.from_text(text)
    print(str(labels1))
    filename = "../templates/atari_basic.labels"
    text = open(filename).read()
    labels2 = Labels.from_text(text)
    labels1.update(labels2)
    filename = "../templates/atari5200.labels"
    text = open(filename).read()
    labels2 = Labels.from_text(text)
    labels1.update(labels2)
    print(str(labels1))
