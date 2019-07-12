#!/usr/bin/env python

import wx

import numpy as np


data = [
    (-1, 0, 0, 350),  # root
    (0, 60, 1, 220),  # 1
    (0, 60, 2, 140),
    (0, 60, 3, 180),
    (0, 100, 4, 140),
    (0, 100, 5, 140),  # 5
    (0, 100, 6, 320),
    (0, 200, 7, 240),
    (1, 180, 8, 260),
    (3, 140, 9, 240),
    (0, 200, 10, 260), # 10
    (1, 200, 11, 240),
    (11, 220, 12, 300),
    (11, 220, 13, 320),
    (3, 100, 14, 260),
]


def get_order(source, parent_level):
    """Find restarts with given parent level.

    Building the list from bottom right up, so first restart at the largest
    frame number is first, then later restarts at the same frame number after
    that. Checkpoints that occur at earlier frames then are added, proceeding
    down to frame zero.
    """
    subset_lookup = {}
    for entry in [d for d in source if d[0] == parent_level]:
        start = entry[1]
        if start not in subset_lookup:
            subset_lookup[start] = []
        subset_lookup[start].append(entry)
        print(entry)
    processing_order = []
    for items in reversed(list(subset_lookup.values())):
        for item in items:
            processing_order.append(item)
            processing_order.extend(get_order(source, item[2]))
    return processing_order


class RestartLine:
    def __init__(self, data, level):
        self.start_frame = data[1]
        self.end_frame = data[3]
        self.parent = data[0]
        self.restart_number = data[2]
        try:
            current_largest_level = max(level[self.start_frame:self.end_frame + 1])
        except ValueError:
            current_largest_level = 0
        self.level = current_largest_level + 1
        level[self.start_frame:self.end_frame + 1] = self.level
        self.interesting_frames = {
            self.start_frame: "Checkpoint from run {self.parent}",
            self.end_frame: "Last frame",
        }

    def __repr__(self):
        return f"{self.restart_number}: {self.start_frame}->{self.end_frame} @ {self.level}"


class RestartLines:
    def __init__(self, processing_order):
        self.lines = [None] * len(processing_order)
        self.last_frame = max([d[3] for d in processing_order])
        self.highest_level = 0
        self.generate_lines(processing_order)

    def __str__(self):
        txt_lines = []
        for line in self.lines:
            txt_lines.append(repr(line))
        return "\n".join(txt_lines)

    def __iter__(self):
        for line in self.lines:
            yield line

    def __getitem__(self, index):
        return self.lines[index]

    def generate_lines(self, processing_order):
        level = np.zeros(self.last_frame, dtype=np.int16) - 1
        for d in processing_order:
            line = RestartLine(d, level)
            self.lines[line.restart_number] = line
            if line.level > self.highest_level:
                self.highest_level = line.level
            #print(level)
            print("generate", line, line.level)

    def find_line(self, frame_number, level):
        for line in self.lines:
            if frame_number >= line.start_frame and frame_number <= line.end_frame and level == line.level:
                return line
        return None


class CheckpointTree(wx.ScrolledWindow):
    def __init__(self, parent, source):
        wx.ScrolledWindow.__init__(self, parent, -1)

        self.width_border = 10
        self.height_border = 10
        self.x_scale = 1
        self.level_height = 10
        self.line_width = 3
        self.marker_size = 3
        self.x_hit = 5
        self.y_hit = 5
        self.over_line = None
        self.scroll_chunk = 20
        self.compute_lines(source)

        self.bg_color = wx.WHITE
        self.line_color = wx.BLUE
        self.marker_color = wx.Colour(255, 255, 255)
        self.cursor_color = wx.Colour(255, 0, 255)
        self.create_dc_stuff()

        self.SetBackgroundColour(self.bg_color)

        self.SetScrollRate(self.scroll_chunk, self.scroll_chunk)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOTION, self.on_motion)

    def compute_lines(self, source=None):
        if source is None:
            source = self.source
        self.source = source
        data = source.get_restart_summary()
        print("DATA", data)
        parent_level = 0
        data.sort()
        order = get_order(data, parent_level)
        order[0:0] = [data[0]]
        from pprint import pprint
        pprint(order)
        lines = RestartLines(order)
        print("restart_lines", lines)
        self.set_lines(lines)

    def recalc_view(self):
        self.compute_lines()

    def refresh_view(self):
        self.Refresh()

    def set_lines(self, lines):
        self.restart_lines = lines
        self.max_width = lines.last_frame * self.x_scale + 2 * self.width_border
        self.max_height = self.level_height * lines.highest_level + 2 * self.height_border
        self.virtual_width = self.max_width
        self.virtual_height = self.max_height
        self.SetVirtualSize((self.max_width, self.max_height))

    def create_dc_stuff(self):
        self.pen = wx.Pen(self.line_color, self.line_width)
        self.hover_pen = wx.Pen(self.line_color, self.line_width * 2 + 1)
        self.marker_brush = wx.Brush(self.marker_color)
        self.marker_pen = wx.Pen(self.line_color, 1)
        self.cursor_brush = wx.Brush(self.cursor_color)

    def on_size(self, event):
        size = self.GetVirtualSize()
        self.virtual_width = size.x
        self.virtual_height = size.y

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        x0, y0 = self.CalcUnscrolledPosition (0, 0)
        dc.SetLogicalOrigin(x0, y0)

        dc.SetPen(self.pen)
        for line in self.restart_lines:
            x1 = self.frame_to_x(line.start_frame)
            x2 = self.frame_to_x(line.end_frame)
            y = self.level_to_y(line.level)
            if line == self.over_line:
                dc.SetPen(self.hover_pen)
                dc.DrawLine(x1, y, x2, y)
            else:
                dc.SetPen(self.pen)
                dc.DrawLine(x1, y, x2, y)
            dc.SetPen(self.marker_pen)
            dc.SetBrush(self.marker_brush)
            for interesting_frame in line.interesting_frames.keys():
                xi = self.frame_to_x(interesting_frame)
                dc.DrawCircle(xi, y, self.marker_size)

            if line.restart_number == 0:
                continue

            # draw vertical line connecting to parent restart
            parent_line = self.restart_lines[line.parent]
            parent_y = self.level_to_y(parent_line.level)
            dc.SetPen(self.pen)
            dc.DrawLine(x1, y, x1, parent_y)

        # current frame & restart number
        xc = self.frame_to_x(self.source.current_frame_number)
        restart = self.source.get_restart_of_frame(self.source.current_frame_number)
        line = self.restart_lines[restart.restart_number]
        yc = self.level_to_y(line.level)
        dc.SetPen(self.marker_pen)
        dc.SetBrush(self.cursor_brush)
        dc.DrawCircle(xc, yc, self.marker_size)

    def frame_to_x(self, frame_number):
        return self.width_border + (self.x_scale * frame_number)

    def level_to_y(self, level):
        return self.virtual_height - (self.height_border + level * self.level_height)

    def on_motion(self, evt):
        ex, ey = evt.GetX(), evt.GetY()
        sx, sy = self.GetViewStart()
        x, y = self.CalcUnscrolledPosition (ex, ey)
        size = self.GetVirtualSize()
        print(ex, sx, x)

        frame_number = (x - self.width_border + self.x_scale // 2) // self.x_scale
        level = ((self.virtual_height - y) - self.height_border + self.level_height // 2) // self.level_height
        x1 = self.frame_to_x(frame_number)
        y1 = self.level_to_y(level)
        # print(x, x1, y, y1, frame_number, level)
        old_over_line = self.over_line
        over_line = None
        if abs(y1 - y) < self.y_hit:
            # print(frame_number, level)
            line = self.restart_lines.find_line(frame_number, level)
            if line:
                print(f"over line {line}")
                over_line = line
            else:
                print(f"not over any line")
        if old_over_line != over_line:
            print("REFRESHING")
            self.over_line = over_line
            wx.CallAfter(self.Refresh)



#For testing 
if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, -1, "Test CheckpointTree", size=(500,400))

    from pprint import pprint

    data.sort()
    pprint(data)

    min_frame = min([d[1] for d in data])
    pprint(min_frame)

    max_frame = max([d[3] for d in data])
    pprint(max_frame)

    parent_level = 0
    order = get_order(data, parent_level)
    order[0:0] = [data[0]]
    pprint(order)

    lines = RestartLines(order)
    print("restart_lines", lines)

    class TestSource:
        def get_restart_summary(self):
            return list(data)

    scroll = CheckpointTree(frame, TestSource())
    frame.Show() 
    app.MainLoop()
