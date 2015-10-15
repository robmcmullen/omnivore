import os

from nose.tools import *

from pyface.tasks.topological_sort import before_after_sort
from omnimon.utils.sortutil import *

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
