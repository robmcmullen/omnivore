import re
import bisect

import numpy as np
import numpy as np

from sawx.utils.command import Command, UndoInfo

from omnivore.utils.searchutil import AlgorithmSearcher

import logging
log = logging.getLogger(__name__)


class FindAllCommand(Command):
    short_name = "find"
    ui_name = "Find"

    def __init__(self, start_caret_index, search_text, error, repeat=False, reverse=False):
        Command.__init__(self)
        self.start_caret_index = start_caret_index
        self.current_caret_index = start_caret_index
        self.search_text = search_text
        self.error = error
        self.repeat = repeat
        self.reverse = reverse
        self.current_match_index = -1
        self.origin = -1
        self.search_copy = None

    def __str__(self):
        return "%s %s" % (self.ui_name, repr(self.search_text))

    def get_search_string(self):
        return bytes.fromhex(self.search_text)

    def get_searchers(self, editor):
        return editor.searchers

    def perform(self, editor, undo):
        self.origin = editor.segment.origin
        self.search_copy = editor.segment.tobytes()
        self.all_matches = []
        self.match_ids = {}
        undo.flags.changed_document = False
        if self.error:
            undo.flags.message = self.error
        else:
            errors = []
            match_dict = {}
            editor.segment.clear_style_bits(match=True)
            searchers = self.get_searchers(editor)
            log.debug(f"Using searchers {searchers}")
            for searcher_cls in searchers:
                try:
                    searcher = searcher_cls(editor, self.search_text, self.search_copy)
                    for start, end in searcher.matches:
                        if start in self.match_ids:
                            if searcher.ui_name not in self.match_ids[start]:
                                self.match_ids[start] +=", %s" % searcher.ui_name
                            if end > match_dict[start]:
                                match_dict[start] = end
                        else:
                            self.match_ids[start] = searcher.ui_name
                            match_dict[start] = end
                except ValueError as e:
                    errors.append(str(e))

            if errors:
                undo.flags.message = " ".join(errors)
            else:
                self.all_matches = [(start, match_dict[start]) for start in sorted(match_dict.keys())]

                #print "Find:", self.all_matches
                if len(self.all_matches) == 0:
                    undo.flags.message = "Not found"
                else:
                    editor.segment.set_style_ranges(self.all_matches, match=True)
                    # Need to use a tuple in order for bisect to search the
                    # list of tuples
                    caret_tuple = (self.current_caret_index, 0)
                    self.current_match_index = bisect.bisect_left(self.all_matches, caret_tuple)
                    if self.current_match_index >= len(self.all_matches):
                        self.current_match_index = 0
                    match = self.all_matches[self.current_match_index]
                    start = match[0]
                    log.debug("Starting at match_index %d = %s" % (self.current_match_index, match))
                    control = editor.focused_viewer.control
                    control.caret_handler.set_caret_from_indexes(start, match[0], match[1])
                    undo.flags.sync_caret_from_control = control
                    undo.flags.message = ("Match %d of %d, found at $%04x in %s" % (self.current_match_index + 1, len(self.all_matches), start + self.origin, self.match_ids[start]))
            undo.flags.refresh_needed = True


class FindNextCommand(Command):
    short_name = "findnext"
    ui_name = "Find Next"

    def __init__(self, search_command):
        Command.__init__(self)
        self.search_command = search_command

    def get_index(self, editor):
        cmd = self.search_command
        caret_tuple = (cmd.current_caret_index, 0)
        match_index = bisect.bisect_right(cmd.all_matches, caret_tuple)
        if match_index == cmd.current_match_index:
            match_index += 1
        if match_index >= len(cmd.all_matches):
            match_index = 0
        cmd.current_match_index = match_index
        return match_index

    def perform(self, editor, undo):
        cmd = self.search_command
        undo.flags.changed_document = False
        index = self.get_index(editor)
        all_matches = cmd.all_matches
        #print "FindNext:", all_matches
        try:
            match = all_matches[index]
            start = match[0]
            control = editor.focused_viewer.control
            control.caret_handler.set_caret_from_indexes(start, match[0], match[1])
            undo.flags.sync_caret_from_control = control
            c = self.search_command
            undo.flags.message = ("Match %d of %d, found at $%04x in %s" % (index + 1, len(all_matches), start + c.origin, c.match_ids[start]))
            cmd.current_caret_index = start
        except IndexError:
            pass
        undo.flags.refresh_needed = True


class FindPrevCommand(FindNextCommand):
    short_name = "findprev"
    ui_name = "Find Previous"

    def get_index(self, editor):
        cmd = self.search_command
        caret_tuple = (cmd.current_caret_index, 0)
        match_index = bisect.bisect_left(cmd.all_matches, caret_tuple)
        match_index -= 1
        if match_index < 0:
            match_index = len(cmd.all_matches) - 1
        cmd.current_match_index = match_index
        return match_index


class FindAlgorithmCommand(FindAllCommand):
    short_name = "findalgorithm"
    ui_name = "Find using expression"

    def get_searchers(self, editor):
        return [AlgorithmSearcher]
