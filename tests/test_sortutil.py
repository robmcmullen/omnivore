import os
import itertools

import numpy as np

from pyface.tasks.topological_sort import before_after_sort
from omnivore.utils.sortutil import *

class SortItem(object):
    def __init__(self, id, before="", after=""):
        self.id = id
        self.before = before
        self.after = after

def check_sorted(items):
    order_lookup = {i.id: items.index(i) for i in items}
    print order_lookup
    wildcards = {}
    for item in items:
        for w in (item.before, item.after):
            if "*" in w and w not in wildcards:
                wildcards[w] = [0, 0]
    if wildcards:
        print "wildcards: %s" % str(wildcards)
        for w in wildcards.keys():
            start = w[:-1]
            pos = 0
            for item in items:
                if item.id.startswith(start):
                    wildcards[w][0] = pos
                    print "found first %s at %s: %s" % (w, pos, item.id)
                    break
                pos += 1
            pos = len(items)
            for item in reversed(items):
                pos -= 1
                if item.id.startswith(start):
                    wildcards[w][1] = pos
                    print "found last %s at %s: %s" % (w, pos, item.id)
                    break
        print "wildcards: %s" % str(wildcards)
    for item in items:
        pos = order_lookup[item.id]
        if item.before:
            if "*" in item.before:
                assert pos < wildcards[item.before][0]
            else:
                assert pos < order_lookup[item.before]
        if item.after:
            if "*" in item.after:
                assert pos > wildcards[item.after][1]
            else:
                assert pos > order_lookup[item.after]

class TestBeforeAfter(object):
    def setup(self):
        self.items = [
            SortItem('z'),
            SortItem('b', after='a'),
            SortItem('a', before='z'),
            ]

    def test_simple(self):
        items = before_after_sort(self.items)
        print ", ".join([i.id for i in items])
        check_sorted(items)

class TestWildcard(object):
    def setup(self):
        self.items = [
            SortItem('z/a'),
            SortItem('z/b'),
            SortItem('z/c'),
            SortItem('z/d'),
            SortItem('a/b', before='z/*'),
            SortItem('a/a', before='z/*'),
            SortItem('b/b', after='a/*'),
            SortItem('b/a'),
            SortItem('m/b', after='b/*'),
            SortItem('m/a'),
            ]

    def test_simple(self):
        items = before_after_wildcard_sort(self.items)
        print ", ".join([i.id for i in items])
        check_sorted(items)

class TestOverlappingRanges(object):
    def setup(self):
        self.items = [
            ([], []),
            ([(1, 2)], [(1, 2)]),
            ([(50, 90), (80, 182)], [(50, 182)]),
            ([(50, 90), (90, 182)], [(50, 182)]),
            ([(50, 90), (91, 182)], [(50, 90), (91, 182)]),
            ([(1, 100), (40, 82)], [(1, 100)]),
            ([(1, 100), (40, 82), (45, 55)], [(1, 100)]),
            ([(1, 100), (40, 82), (45, 55), (88, 200)], [(1, 200)]),
            ([(373, 440), (486, 537), (181, 182)], [(181, 182), (373, 440), (486, 537)]),
            ([(183, 182), (181, 182)], [(181, 183)]),
            ]

    def test_simple(self):
        for before, after in self.items:
            for p in itertools.permutations(before):
                processed = collapse_overlapping_ranges(p)
                print p, processed, after
                assert processed == after

class TestInvertRanges(object):
    def setup(self):
        self.items = [
            ([], 10, [(0, 10)]),
            ([(1, 2)], 10, [(0, 1), (2, 10)]),
            ([(50, 182)], 200, [(0, 50), (182, 200)]),
            ([(50, 90), (91, 182)], 200, [(0, 50), (90, 91), (182, 200)]),
            ([(181, 182), (373, 440), (486, 537)], 600, [(0, 181), (182, 373), (440, 486), (537, 600)]),
            ]

    def test_simple(self):
        for before, size, after in self.items:
            processed = invert_ranges(before, size)
            print size, before, processed, after
            assert processed == after
            processed = invert_ranges(after, size)
            assert processed == before
            print size, before, processed, after

class TestInvertRects(object):
    def setup(self):
        self.items = [
            ([[(5, 16), (8, 21)], ], 10, 50, [[(0, 0), (5, 16)], [(0, 16), (5, 21)], [(0, 21), (5, 50)], [(5, 0), (8, 16)], [(5, 21), (8, 50)], [(8, 0), (10, 16)], [(8, 16), (10, 21)], [(8, 21), (10, 50)]]),
            ]

    def test_simple(self):
        for before, rows, cols, after in self.items:
            processed = invert_rects(before, rows, cols)
            print rows, cols, before, processed, after
            assert processed == after

class TestRangeToIndex(object):
    def setup(self):
        self.items = [
            ([(50, 56)], (50, 51, 52, 53, 54, 55)),
            ([(50, 56), (60, 62)], (50, 51, 52, 53, 54, 55, 60, 61)),
            ([(50, 56), (60, 62), (70, 73)], (50, 51, 52, 53, 54, 55, 60, 61, 70, 71, 72)),
            ]

    def test_simple(self):
        for before, after in self.items:
            processed = ranges_to_indexes(before)
            after = np.asarray(after)
            print before, processed, after
            np.testing.assert_array_equal(processed, after)

if __name__ == "__main__":
    t = TestRangeToIndex()
    t.setup()
    t.test_simple()
