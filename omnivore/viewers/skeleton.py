import os
import sys

import numpy as np

import wx

from atrip import Container, Segment

from sawx.ui import compactgrid as cg
from ..editors.linked_base import VirtualTableLinkedBase

from ..ui.segment_grid import SegmentGridControl

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)



class SampleVirtualTable(cg.VirtualTable):
    column_labels = ["Target", "Count", "Flag", "Type", "^Values"]
    column_sizes = [4, 2, 2, 2, 40]

    def __init__(self, linked_base):
        self.virtual_linked_base = linked_base
        s = linked_base.segment
        cg.VirtualTable.__init__(self, len(self.column_labels), s.origin)

    def calc_num_rows(self):
        num_cols = self.items_per_row
        return (self.virtual_linked_base.document_length + num_cols - 1) // num_cols

    def calc_last_valid_index(self):
        return self.virtual_linked_base.document_length

    def get_label_at_index(self, index):
        return str(index)

    def get_value_style(self, row, col):
        text = f"r{row}c{col}"
        s = self.virtual_linked_base.segment
        index, _ = self.get_index_range(row, col)
        style = s.style[index]
        return text, style

    def rebuild(self):
        v = self.virtual_linked_base
        old_size = v.document_length
        size = old_size + 1
        old_segment = v.segment
        container = Container(np.arange(size, dtype=np.uint8))
        segment = Segment(container)
        segment.style[0:old_size] = old_segment.style[0:old_size]
        v.segment = segment
        self.init_boundaries()
        print(f"new size: {len(v.segment)}")


class SampleGridControl(SegmentGridControl):
    default_table_cls = SampleVirtualTable

    def calc_default_table(self, linked_base):
        return self.default_table_cls(linked_base)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        self.table.rebuild()
        cg.CompactGrid.recalc_view(self)

    def refresh_view(self):
        if self.IsShown():
            log.debug("refreshing %s" % self)
            self.recalc_view()
        else:
            log.debug("skipping refresh of hidden %s" % self)


class VirtualTestViewer(SegmentViewer):
    name = "vtest"

    ui_name = "Virtual Test Viewer"

    control_cls = SampleGridControl

    # initialization

    @classmethod
    def replace_linked_base(cls, linked_base):
        # the new linked base decouples the cursor here from the other segments
        segment = DefaultSegment(np.arange(400, dtype=np.uint8))
        return VirtualTableLinkedBase(editor=linked_base.editor, segment=segment)

    def create_post(self):
        self.linked_base.table = self.control.table

    # properties

    @property
    def table(self):
        return self.control.table

    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    def byte_style_changed(self, index_range):
        log.debug("byte_style_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    def recalc_data_model(self):
        self.table.rebuild()

    def do_priority_level_refresh(self):
        self.control.recalc_view()
        self.refresh_view(True)
