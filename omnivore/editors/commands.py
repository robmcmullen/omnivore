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

    def __init__(self, start_cursor_index, search_text, error, repeat=False, reverse=False):
        Command.__init__(self)
        self.start_cursor_index = start_cursor_index
        self.search_text = search_text
        self.error = error
        self.repeat = repeat
        self.reverse = reverse
        self.current_match_index = -1
        self.origin = -1

    def __str__(self):
        return "%s %s" % (self.ui_name, repr(self.search_text))

    def get_search_string(self):
        return bytes.fromhex(self.search_text)

    def get_searchers(self, editor):
        return editor.searchers

    def perform(self, editor, undo):
        self.origin = editor.segment.origin
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
                # Need to use a tuple in order for bisect to search the list
                # of tuples
                    cursor_tuple = (editor.cursor_index, 0)
                    self.current_match_index = bisect.bisect_left(self.all_matches, cursor_tuple)
                    if self.current_match_index >= len(self.all_matches):
                        self.current_match_index = 0
                    match = self.all_matches[self.current_match_index]
                    start = match[0]
                    log.debug("Starting at match_index %d = %s" % (self.current_match_index, match))
                    undo.flags.index_range = match
                    undo.flags.cursor_index = start
                    undo.flags.select_range = True
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
        cursor_tuple = (editor.cursor_index, 0)
        match_index = bisect.bisect_right(cmd.all_matches, cursor_tuple)
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
            undo.flags.cursor_index = start
            undo.flags.select_range = True
            c = self.search_command
            undo.flags.message = ("Match %d of %d, found at $%04x in %s" % (index + 1, len(all_matches), start + c.origin, c.match_ids[start]))
        except IndexError:
            pass
        undo.flags.refresh_needed = True


class FindPrevCommand(FindNextCommand):
    short_name = "findprev"
    ui_name = "Find Previous"

    def get_index(self, editor):
        cmd = self.search_command
        cursor_tuple = (editor.cursor_index, 0)
        match_index = bisect.bisect_left(cmd.all_matches, cursor_tuple)
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
