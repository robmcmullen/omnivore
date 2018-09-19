import os
import sys

import numpy as np

import wx

from traits.api import on_trait_change, Bool, Undefined, Any, Instance

from atrcopy import DefaultSegment
from omni8bit.udis_fast import libudis

from omnivore.utils.wx import compactgrid as cg
from omnivore8bit.byte_edit.linked_base import VirtualLinkedBase

from ..ui.segment_grid import SegmentGridControl

from . import SegmentViewer

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
        return (self.virtual_linked_base.document_length + 4) // 5

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
        pass


class SampleGridControl(SegmentGridControl):
    default_table_cls = SampleVirtualTable

    def calc_default_table(self):
        return self.default_table_cls(self.caret_handler)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=self.default_table_cls.column_sizes, col_labels=self.default_table_cls.column_labels)

    def recalc_view(self):
        cg.CompactGrid.recalc_view(self)


class VirtualTestViewer(SegmentViewer):
    name = "vtest"

    pretty_name = "Virtual Test Viewer"

    control_cls = SampleGridControl

    has_cpu = True

    has_hex = True

    # trait defaults

    # initialization

    @classmethod
    def replace_linked_base(cls, linked_base):
        # the new linked base decouples the cursor here from the other segments
        segment = DefaultSegment(np.arange(400, dtype=np.uint8))
        return VirtualLinkedBase(editor=linked_base.editor, segment=segment)

    # properties

    @property
    def table(self):
        return self.control.table

    @on_trait_change('linked_base.editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.restart_disassembly(index_range)

    @on_trait_change('linked_base.editor.document.byte_style_changed')
    def byte_style_changed(self, index_range):
        log.debug("byte_style_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.table.rebuild()

    def recalc_data_model(self):
        self.table.rebuild()
