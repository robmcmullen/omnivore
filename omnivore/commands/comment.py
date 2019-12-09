import numpy as np

from . import ChangeStyleCommand

import logging
log = logging.getLogger(__name__)


class SetCommentCommand(ChangeStyleCommand):
    short_name = "set_comment"
    ui_name = "Comment"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('text', 'string'),
            ]

    def __init__(self, segment, ranges, text):
        ChangeStyleCommand.__init__(self, segment)
        # Only use the first byte of each range
        self.ranges = self.convert_ranges(ranges)
        log.debug("%s operating on ranges: %s" % (self.ui_name, str(ranges)))
        self.text = text
        # indexes = ranges_to_indexes(self.ranges)
        # self.index_range = indexes[0], indexes[-1]
        # if len(ranges) == 1:
        #     self.ui_name = "%s @ %04x" % (self.ui_name, self.segment.origin + indexes[0])

    def __str__(self):
        if len(self.text) > 20:
            text = self.text[:20] + "..."
        else:
            text = self.text
        return "%s: %s" % (self.ui_name, text)

    def convert_ranges(self, ranges):
        return tuple([(items[0], items[0] + 1) for items in ranges])

    def set_undo_flags(self, flags):
        flags.byte_style_changed = True
        # flags.index_range = self.index_range

    def clamp_ranges_and_indexes(self, editor):
        return self.ranges, None

    def change_comments(self, ranges, indexes):
        self.segment.set_comment_ranges(ranges, self.text)

    def do_change(self, editor, undo):
        ranges, indexes = self.clamp_ranges_and_indexes(editor)
        old_data = self.segment.get_comment_restore_data(ranges)
        self.change_comments(ranges, indexes)
        return old_data

    def undo_change(self, editor, old_data):
        self.segment.restore_comments(old_data)


class ClearCommentCommand(SetCommentCommand):
    short_name = "clear_comment"
    ui_name = "Remove Comment"

    def __init__(self, segment, ranges):
        SetCommentCommand.__init__(self, segment, ranges, "")

    def convert_ranges(self, ranges):
        # When clearing comments, we want to look at every space, not just the
        # first byte of each range like setting comments
        return ranges

    def change_comments(self, ranges, indexes):
        self.segment.clear_comment_ranges(ranges)


class PasteCommentsCommand(ClearCommentCommand):
    short_name = "paste_comments"
    ui_name = "Paste Comments"
    serialize_order =  [
            ('segment', 'int'),
            ('ranges', 'int_list'),
            ('cursor', 'int'),
            ('bytes', 'string'),
            ]

    def __init__(self, segment, ranges, cursor, bytes, *args, **kwargs):
        # remove zero-length ranges
        r = [(start, end) for start, end in ranges if start != end]
        ranges = r
        if not ranges:
            # use the range from cursor to end
            ranges = [(cursor, len(segment))]
        ClearCommentCommand.__init__(self, segment, ranges, bytes)
        self.cursor = cursor
        self.comments = bytes.tostring().splitlines()
        self.num_lines = len(self.comments)

    def __str__(self):
        return "%s: %d line%s" % (self.ui_name, self.num_lines, "" if self.num_lines == 1 else "s")

    def clamp_ranges_and_indexes(self, editor):
        disasm = editor.disassembly.table.disassembler
        count = self.num_lines
        comment_indexes = []
        clamped = []
        for start, end in self.ranges:
            index = start
            log.debug("starting range %d:%d" % (start, end))
            while index < end and count > 0:
                comment_indexes.append(index)
                pc = index + self.segment.origin
                log.debug("comment at %d, %04x" % (index, pc))
                try:
                    index = disasm.get_next_instruction_pc(pc)
                    count -= 1
                except IndexError:
                    count = 0
            clamped.append((start, index))
            if count <= 0:
                break
        return clamped, comment_indexes

    def change_comments(self, ranges, indexes):
        """Add comment lines as long as we don't go out of range (if specified)
        or until the end of the segment or the comment list is exhausted.

        Depends on a valid disassembly to find the lines; we are adding a
        comment for the first byte in each statement.
        """
        log.debug("ranges: %s" % str(ranges))
        log.debug("indexes: %s" % str(indexes))
        self.segment.set_comments_at_indexes(ranges, indexes, self.comments)
        self.segment.set_style_at_indexes(indexes, comment=True)
