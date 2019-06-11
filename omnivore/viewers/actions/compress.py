"""Segment actions
"""
import os
import sys

import wx

from atrip import Container, Collection
from atrip.compressor import find_compressor_by_name

from . import ViewerSubAction
from ...document import DiskImageDocument

from ... import commands
from ... import errors

import logging
log = logging.getLogger(__name__)


class compress_select(ViewerSubAction):
    def calc_enabled(self, action_key):
        return self.viewer.control.caret_handler.has_selection

    def perform(self, action_key):
        compressor_name = self.action_list_id
        compressor = find_compressor_by_name(compressor_name)
        log.debug(f"compressing with {compressor_name}")
        data = self.viewer.copy_data_from_selections()
        compressed = compressor.calc_packed_data(data)
        log.debug(f"data size={len(data)}, compressed={len(compressed)}")
        container = Container(compressed)
        collection = Collection(compressor_name, container=container)
        file_metadata = {'uri': compressor_name, 'mime': 'application/octet-stream', 'atrip_collection': collection}
        document = DiskImageDocument(file_metadata)
        self.viewer.frame.add_document(document)
