#!/usr/bin/env python
""" doc string """
import os
from cStringIO import StringIO

globalvar="string"
listvar=[1,2,3,5,7,11]
dictvar={'a':1,'b':2,'z'=3333}

class Foo(Bar):
    classvar="stuff"
    def __init__(self):
        self.baz="zippy"
        if self.baz=str(globalvar):
            open(self.baz)
        else:
            raise TypeError("stuff")
        return
