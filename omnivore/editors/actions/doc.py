"""Byte modification actions
"""
import os
import sys

import wx

from omnivore_framework.action import OmnivoreAction, OmnivoreRadioListAction

from ... import commands
from ... import errors
from ...disassembler import valid_cpus, processors
from ...utils.archutil import calc_available_memory_maps, available_memory_maps

import logging
log = logging.getLogger(__name__)


class doc_cpu(OmnivoreRadioListAction):
    prefix = "doc_cpu_"

    def calc_name(self, action_key):
        cpu_name = self.get_item(action_key)
        return processors[cpu_name]["description"]

    def calc_list_items(self):
        return valid_cpus

    def calc_checked_list_item(self, action_key, index, item):
        return self.editor.document.cpu == item

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.editor.document.cpu = item

class doc_os_labels(OmnivoreRadioListAction):
    prefix = "doc_os_"

    def calc_name(self, action_key):
        item = self.get_item(action_key)
        return str(item)

    def calc_list_items(self):
        items = sorted(calc_available_memory_maps().values())
        return items

    def calc_checked_list_item(self, action_key, index, item):
        return self.editor.document.operating_system == item.keyword

    def perform(self, action_key):
        item = self.get_item(action_key)
        self.editor.document.operating_system = item.keyword
