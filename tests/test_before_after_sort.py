import os

from nose.tools import *

from pyface.tasks.topological_sort import before_after_sort
from peppy2.utils.sortutil import *

class SortItem(object):
    def __init__(self, id, before="", after=""):
        self.id = id
        self.before = before
        self.after = after

class TestBeforeAfter(object):
    def setup(self):
        self.items = [
            SortItem('z'),
            SortItem('b', after='a'),
            SortItem('a', before='z'),
            ]
        
    def check_sorted(self, items):
        order_lookup = {i.id: items.index(i) for i in items}
        print order_lookup
        for item in items:
            pos = order_lookup[item.id]
            if item.before:
                assert pos < order_lookup[item.before]
            if item.after:
                assert pos > order_lookup[item.after]

    def test_simple(self):
        items = before_after_sort(self.items)
        print ", ".join([i.id for i in items])
        self.check_sorted(items)
