import os
import itertools

import numpy as np
import pytest

import mock
from omnivore_framework.utils import textutil


class TestIntLabelDict(object):
    def setup(self):
        pass

    def test_simple(self):
        items = [
            ("12 a", {12: "a"}),
            ("12 a\n14 b\n$20 c", {12: "a", 14: "b", 0x20: "c"}),
            ("$12 a", {0x12: "a"}),
            ("$12 whatever and stuff", {0x12: "whatever"}),
            ("$cd !@#$ whatEver", {0xcd: "whatEver"}),
            (">]}**  $1F !@#$ what_ever", {0x1f: "what_ever"}),
            ("No labels defined in here", {}),
        ]

        for search_text, expected in items:
            d = textutil.parse_int_label_dict(search_text)
            print(search_text, d)
            assert expected == d

    def test_with_equals(self):
        items = [
            ("a=12", {12: "a"}),
            ("a = 12", {12: "a"}),
            ("a =12", {12: "a"}),
            ("a= 12", {12: "a"}),
            ("a= 12\n14 b\nc=$20", {12: "a", 14: "b", 0x20: "c"}),
            ("$12 a", {0x12: "a"}),
            ("whatever and stuff = $12", {0x12: "stuff"}),
            ("u_ = 1234#address", {1234: "u_"}),
            ("_u = 1234    # address", {1234: "_u"}),
            ("No = labels = defined = in here", {}),
        ]

        for search_text, expected in items:
            d = textutil.parse_int_label_dict(search_text, allow_equals=True)
            print(search_text, d)
            assert expected == d

if __name__ == "__main__":
    t = TestIntLabelDict()
    t.setup()
    t.test_simple()
    t.test_with_equals()
