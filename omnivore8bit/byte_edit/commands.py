import re
import bisect

import fs
import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Command, UndoInfo
from omnivore8bit.commands import SegmentCommand, ChangeMetadataCommand, SetContiguousDataCommand, SetRangeCommand, SetRangeValueCommand
from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges
from omnivore8bit.utils.searchalgorithm import AlgorithmSearcher
from omnivore.utils.file_guess import FileGuess
from omnivore.utils.permute import bit_reverse_table

import logging
log = logging.getLogger(__name__)
progress_log = logging.getLogger("progress")


class ChangeByteCommand(SetContiguousDataCommand):
    short_name = "cb"
    pretty_name = "Change Bytes"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ('caret_at_end', 'bool'),
            ('ignore_if_same_bytes', 'bool'),
            ]

    def __init__(self, segment, start_index, end_index, bytes, caret_at_end=False, ignore_if_same_bytes=False, advance=False):
        SetContiguousDataCommand.__init__(self, segment, start_index, end_index, advance=advance)
        self.data = bytes
        self.caret_at_end = caret_at_end
        self.ignore_if_same_bytes = ignore_if_same_bytes

    def get_data(self, orig):
        return self.data


class CoalescingChangeByteCommand(ChangeByteCommand):
    short_name = "ccb"

    def can_coalesce(self, next_command):
        return next_command.start_index == self.start_index and next_command.end_index == self.end_index

    def coalesce_merge(self, next_command):
        self.data = next_command.data


class InsertFileCommand(SetContiguousDataCommand):
    short_name = "in"
    pretty_name = "Insert File"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('uri', 'string'),
            ]

    def __init__(self, segment, start_index, uri):
        SetContiguousDataCommand.__init__(self, segment, start_index, -1)
        self.uri = uri
        self.error = None

    def get_data(self, orig):
        try:
            guess = FileGuess(self.uri)
        except fs.errors.FSError, e:
            self.error = "File load error: %s" % str(e)
            return
        data = guess.numpy
        if len(orig) < len(data):
            data = data[0:len(orig)]
        return data

    def perform(self, editor, undo):
        i1 = self.start_index
        orig = self.segment.data[self.start_index:]
        data = self.get_data(orig)
        if self.error:
            undo.flags.message = self.error
        else:
            i2 = i1 + len(data)
            self.end_index = i2
            undo.flags.byte_values_changed = True
            undo.flags.index_range = i1, i2
            undo.flags.select_range = True
            old_data = self.segment[i1:i2].copy()
            self.segment[i1:i2] = data
            undo.data = (old_data,)


class MiniAssemblerCommand(ChangeByteCommand):
    short_name = "asm"
    pretty_name = "Asm"
    serialize_order =  [
            ('segment', 'int'),
            ('start_index', 'int'),
            ('end_index', 'int'),
            ('bytes', 'string'),
            ('asm', 'string'),
            ]

    def __init__(self, segment, start_index, end_index, bytes, asm):
        ChangeByteCommand.__init__(self, segment, start_index, end_index, bytes)
        self.asm = asm

    def __str__(self):
        return "%s @ %04x" % (self.asm, self.start_index)


class SetCommentCommand(ChangeMetadataCommand):
    short_name = "set_comment"
    pretty_name = "Comment"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('text', 'string'),
            ]

    def __init__(self, segment, ranges, text):
        ChangeMetadataCommand.__init__(self, segment)
        # Only use the first byte of each range
        self.ranges = self.convert_ranges(ranges)
        log.debug("%s operating on ranges: %s" % (self.pretty_name, str(ranges)))
        self.text = text
        indexes = ranges_to_indexes(self.ranges)
        self.index_range = indexes[0], indexes[-1]
        if len(ranges) == 1:
            self.pretty_name = "%s @ %04x" % (self.pretty_name, self.segment.start_addr + indexes[0])

    def __str__(self):
        if len(self.text) > 20:
            text = self.text[:20] + "..."
        else:
            text = self.text
        return "%s: %s" % (self.pretty_name, text)

    def convert_ranges(self, ranges):
        return tuple([(start, start + 1) for start, end in ranges])

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True
        flags.index_range = self.index_range

    def clamp_ranges_and_indexes(self, editor):
        return self.ranges, None

    def change_comments(self, ranges, indexes):
        self.segment.set_comment(ranges, self.text)

    def do_change(self, editor, undo):
        ranges, indexes = self.clamp_ranges_and_indexes(editor)
        old_data = self.segment.get_comment_restore_data(ranges)
        self.change_comments(ranges, indexes)
        return old_data

    def undo_change(self, editor, old_data):
        self.segment.restore_comments(old_data)


class ClearCommentCommand(SetCommentCommand):
    short_name = "clear_comment"
    pretty_name = "Remove Comment"

    def __init__(self, segment, ranges, bytes=""):
        SetCommentCommand.__init__(self, segment, ranges, bytes)

    def convert_ranges(self, ranges):
        # When clearing comments, we want to look at every space, not just the
        # first byte of each range like setting comments
        return ranges

    def change_comments(self, ranges, indexes):
        self.segment.clear_comment(ranges)


class SetLabelCommand(ChangeMetadataCommand):
    short_name = "set_comment"
    pretty_name = "Label"
    serialize_order =  [
            ('segment', 'int'),
            ('addr', 'addr'),
            ('label', 'string'),
            ]

    def __init__(self, segment, addr, label):
        ChangeMetadataCommand.__init__(self, segment)
        self.addr = addr
        self.label = label

    def __str__(self):
        if len(self.label) > 20:
            text = self.label[:20] + "..."
        else:
            text = self.label
        return "%s: %s" % (self.pretty_name, text)

    def do_change(self, editor, undo):
        old = self.segment.memory_map.get(self.addr, None)
        self.segment.memory_map[self.addr] = self.label
        return old

    def undo_change(self, editor, old_data):
        if old_data is None:
            self.segment.memory_map.pop(self.addr, "")
        else:
            self.segment.memory_map[self.addr] = old_data


class ClearLabelCommand(ChangeMetadataCommand):
    short_name = "clear_comment"
    pretty_name = "Remove Label"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ]

    def __init__(self, segment, ranges):
        ChangeMetadataCommand.__init__(self, segment)
        print ranges
        self.ranges = ranges

    def do_change(self, editor, undo):
        print self.ranges
        indexes = ranges_to_indexes(self.ranges)
        origin = self.segment.start_addr
        old = {}
        for i in indexes:
            addr = i + origin
            old[addr] = self.segment.memory_map.get(addr, None)
            self.segment.memory_map.pop(addr, "")
        return old

    def undo_change(self, editor, old_data):
        if old_data is not None:
            indexes = ranges_to_indexes(self.ranges)
            for addr, label in old_data.iteritems():
                if label is None:
                    self.segment.memory_map.pop(addr, "")
                else:
                    self.segment.memory_map[addr] = label


class RevertToBaselineCommand(SetRangeCommand):
    short_name = "revert_baseline"
    pretty_name = "Revert to Baseline Data"

    def get_baseline_data(self, orig, editor, indexes):
        r = editor.document.baseline_document.container_segment.get_parallel_raw_data(self.segment)
        return r[indexes].data

    def do_change(self, editor, undo):
        indexes = ranges_to_indexes(self.ranges)
        undo.flags.index_range = indexes[0], indexes[-1]
        old_data = self.segment[indexes].copy()
        self.segment[indexes] = self.get_baseline_data(old_data, editor, indexes)
        return old_data


class FindAllCommand(Command):
    short_name = "find"
    pretty_name = "Find"

    def __init__(self, start_caret_index, search_text, error, repeat=False, reverse=False):
        Command.__init__(self)
        self.start_caret_index = start_caret_index
        self.search_text = search_text
        self.error = error
        self.repeat = repeat
        self.reverse = reverse
        self.current_match_index = -1
        self.start_addr = -1

    def __str__(self):
        return "%s %s" % (self.pretty_name, repr(self.search_text))

    def get_search_string(self):
        return bytearray.fromhex(self.search_text)

    def get_searchers(self, editor):
        return editor.searchers

    def perform(self, editor, undo):
        self.start_addr = editor.segment.start_addr
        self.all_matches = []
        self.match_ids = {}
        undo.flags.changed_document = False
        if self.error:
            undo.flags.message = self.error
        else:
            errors = []
            match_dict = {}
            editor.segment.clear_style_bits(match=True)
            for searcher_cls in self.get_searchers(editor):
                try:
                    searcher = searcher_cls(editor, self.search_text)
                    for start, end in searcher.matches:
                        if start in self.match_ids:
                            if searcher.pretty_name not in self.match_ids[start]:
                                self.match_ids[start] +=", %s" % searcher.pretty_name
                            if end > match_dict[start]:
                                match_dict[start] = end
                        else:
                            self.match_ids[start] = searcher.pretty_name
                            match_dict[start] = end
                except ValueError, e:
                    errors.append(str(e))

            if errors:
                undo.flags.message = " ".join(errors)
            else:
                self.all_matches = [(start, match_dict[start]) for start in sorted(match_dict.keys())]

                #print "Find:", self.all_matches
                if len(self.all_matches) == 0:
                    undo.flags.message = "Not found"
                    editor.document.change_count += 1  # FIXME: find a better way to do this. This is needed to force grid controls to change in order to remove highlights
                else:
                # Need to use a tuple in order for bisect to search the list
                # of tuples
                    caret_tuple = (editor.linked_base.caret_index, 0)
                    self.current_match_index = bisect.bisect_left(self.all_matches, caret_tuple)
                    if self.current_match_index >= len(self.all_matches):
                        self.current_match_index = 0
                    match = self.all_matches[self.current_match_index]
                    start = match[0]
                    log.debug("Starting at match_index %d = %s" % (self.current_match_index, match))
                    undo.flags.index_range = match
                    undo.flags.caret_index = start
                    undo.flags.select_range = True
                    undo.flags.message = ("Match %d of %d, found at $%04x in %s" % (self.current_match_index + 1, len(self.all_matches), start + self.start_addr, self.match_ids[start]))
            undo.flags.refresh_needed = True


class FindNextCommand(Command):
    short_name = "findnext"
    pretty_name = "Find Next"

    def __init__(self, search_command):
        Command.__init__(self)
        self.search_command = search_command

    def get_index(self, editor):
        cmd = self.search_command
        caret_tuple = (editor.linked_base.caret_index, 0)
        match_index = bisect.bisect_right(cmd.all_matches, caret_tuple)
        if match_index == cmd.current_match_index:
            match_index += 1
        if match_index >= len(cmd.all_matches):
            match_index = 0
        cmd.current_match_index = match_index
        return match_index

    def perform(self, editor, undo):
        undo.flags.changed_document = False
        index = self.get_index(editor)
        all_matches = self.search_command.all_matches
        #print "FindNext:", all_matches
        try:
            match = all_matches[index]
            start = match[0]
            undo.flags.index_range = match
            undo.flags.caret_index = start
            undo.flags.select_range = True
            c = self.search_command
            undo.flags.message = ("Match %d of %d, found at $%04x in %s" % (index + 1, len(all_matches), start + c.start_addr, c.match_ids[start]))
        except IndexError:
            pass
        undo.flags.refresh_needed = True


class FindPrevCommand(FindNextCommand):
    short_name = "findprev"
    pretty_name = "Find Previous"

    def get_index(self, editor):
        cmd = self.search_command
        caret_tuple = (editor.linked_base.caret_index, 0)
        match_index = bisect.bisect_left(cmd.all_matches, caret_tuple)
        match_index -= 1
        if match_index < 0:
            match_index = len(cmd.all_matches) - 1
        cmd.current_match_index = match_index
        return match_index


class FindAlgorithmCommand(FindAllCommand):
    short_name = "findalgorithm"
    pretty_name = "Find using expression"

    def get_searchers(self, editor):
        return [AlgorithmSearcher]


class SetSegmentOriginCommand(SegmentCommand):
    short_name = "setsegorg"
    pretty_name = "Segment Origin"
    serialize_order =  [
            ('segment', 'int'),
            ('origin', 'int'),
            ]

    def __init__(self, segment, origin):
        SegmentCommand.__init__(self, segment)
        self.origin = origin

    def __str__(self):
        return "%s: $%04x" % (self.pretty_name, self.origin)

    def set_undo_flags(self, flags):
        flags.metadata_dirty = True
        flags.rebuild_ui = True

    def do_change(self, editor, undo):
        old_origin = self.segment.start_addr
        self.segment.start_addr = self.origin
        return old_origin

    def undo_change(self, editor, old_data):
        self.segment.start_addr = old_data


class SegmentMemoryMapCommand(ChangeMetadataCommand):
    short_name = "seg_memmap"
    pretty_name = "Segment Memory Map"
    serialize_order =  [
            ('segment', 'int'),
            ('memory_map', 'dict'),
            ]

    def __init__(self, segment, memory_map):
        ChangeMetadataCommand.__init__(self, segment)
        self.memory_map = memory_map

    def do_change(self, editor, undo):
        old_data = dict(editor.segment.memory_map)
        editor.segment.memory_map = self.memory_map
        return old_data

    def undo_change(self, editor, old_data):
        editor.segment.memory_map = old_data
