import re

import numpy as np

from sawx.utils.parseutil import NumpyIntExpression, ParseException

import logging
log = logging.getLogger(__name__)


class BaseSearcher(object):
    ui_name = "<base class>"

    def __init__(self, editor, search_text, search_copy, **kwargs):
        self.search_text = self.get_search_text(search_text)
        self.search_copy = search_copy
        if len(self.search_text) > 0:
            self.matches = self.get_matches(editor)
        else:
            self.matches = []

    def get_search_text(self, text):
        return bytes(text, "utf-8")

    def get_matches(self, editor):
        text = self.search_copy
        rs = re.escape(bytes(self.search_text))
        matches = [(i.start(), i.end()) for i in re.finditer(rs, text)]
        return matches


class HexSearcher(BaseSearcher):
    ui_name = "hex"

    def __str__(self):
        return "hex matches: %s" % str(self.matches)

    def get_search_text(self, text):
        try:
            return bytes.fromhex(text)
        except ValueError:
            log.debug("%s: fromhex failed on: %s")
            return ""


class CharSearcher(BaseSearcher):
    ui_name = "text"

    def __str__(self):
        return "char matches: %s" % str(self.matches)


class CommentSearcher(BaseSearcher):
    ui_name = "comments"

    def __str__(self):
        return "comment matches: %s" % str(self.matches)

    def get_search_text(self, text):
        return text

    def get_matches(self, editor):
        segment = editor.segment
        s = segment.origin
        matches = []
        if editor.last_search_settings.get('match_case', False):
            search_text = self.search_text
            for index, comment in segment.iter_comments_in_segment():
                if search_text in comment:
                    matches.append((index, index + 1))
        else:
            search_text = self.search_text.lower()
            for index, comment in segment.iter_comments_in_segment():
                if search_text in comment.lower():
                    matches.append((index, index + 1))
        return matches


class AlgorithmSearcher(BaseSearcher):
    def __str__(self):
        return "pyparsing matches: %s" % str(self.matches)

    def get_search_text(self, text):
        return text

    def get_matches(self, editor):
        s = editor.segment
        a = np.arange(s.origin, s.origin + len(s))
        b = np.asarray(self.search_copy, dtype=np.uint8)
        v = {
            'a': a,
            'b': b,
            }
        expression = NumpyIntExpression(v)
        try:
            result = expression.eval(self.search_text)
            matches = s.bool_to_ranges(result)
            return matches
        except ParseException as e:
            raise ValueError(e)


known_searchers = [
    HexSearcher,
#    CharSearcher,
#    DisassemblySearcher,
#    CommentSearcher,
    ]
