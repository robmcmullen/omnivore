#!/usr/bin/env python

import numpy as np

import wx

import  wx.lib.buttons  as  buttons

from omnivore.utils.wx.info_panels import InfoPanel

#----------------------------------------------------------------------


from atrcopy import DefaultSegment, SegmentData

class MockEditor(object):
    def __init__(self, segment):
        self.segment = segment

    def change_bytes(self, start, end, bytes):
        print "changing bytes %d-%d to %s" % (start, end, repr(bytes))

class MockTask(object):
    def __init__(self, editor):
        self.active_editor = editor


fields = [
    ("text", "Level Number", 0x00, 2),
    ("text", "Level Name", 0x3ec, 20),
    ("colors", "Game Colors", 0x2a, 9),
    ("int", "Points per Peanut", 0x33, 2),
    ("int", "Bonus Value", 0x35, 2),
    ("int", "Number of Bullets", 0x3d, 1),
    ("int", "Number of Peanuts to Finish", 0x3e, 1),
]

class MyFrame(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.DefaultSize)
        data = np.arange(0x800, dtype=np.uint8)
        data[0:0x50] = np.fromstring("01\x1b1\x1b1\x1b1\xa0I\xc6\x94\xaax\x0f\x00\x00B\x80E\x1b1\xe00:\xbe\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Ws\x8e\xab\x00\x00\x86\x86\x0fT\x86\x8a\xff\xca\x00d\x00\xd0\x07\x00,F,\x80(\x01\x10L\xfdO!\x00\x00L\x00\x00 K(`\xff\x00\x8e,", dtype=np.uint8)
        data[0x3ec:0x400] = np.fromstring("abdceabdceabcdeabcde", dtype=np.uint8)
        r = SegmentData(data)
        segment = DefaultSegment(r, 0x2800)
        editor = MockEditor(segment)
        task = MockTask(editor)
        self.info = InfoPanel(self, task, fields)
        self.info.recalc_view()

class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, -1, 'test_column_autosize.py')
        frame.Show(True)
        frame.Centre()
        return True

if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()
