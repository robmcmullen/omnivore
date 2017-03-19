import re


class BaseSearcher(object):
    pretty_name = "<base class>"

    def __init__(self, editor, search_text, **kwargs):
        self.search_text = self.get_search_text(search_text)
        if len(self.search_text) > 0:
            self.matches = self.get_matches(editor)
            self.set_style(editor)
        else:
            self.matches = []
    
    def get_search_text(self, text):
        return bytearray(text, "utf-8")
    
    def get_matches(self, editor):
        text = editor.segment.search_copy
        rs = re.escape(str(self.search_text))
        matches = [(i.start(), i.end()) for i in re.finditer(rs, text)]
        return matches
    
    def set_style(self, editor):
        editor.segment.set_style_ranges(self.matches, match=True)

class HexSearcher(BaseSearcher):
    pretty_name = "hex"

    def __str__(self):
        return "hex matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return bytearray.fromhex(text)

class CharSearcher(BaseSearcher):
    pretty_name = "text"
    
    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.match_case = match_case
        self.find_inverse = find_inverse
        BaseSearcher.__init__(self, editor, search_text)
    
    def __str__(self):
        return "char matches: %s" % str(self.matches)

class DisassemblySearcher(BaseSearcher):
    pretty_name = "disasm"

    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.match_case = match_case
        self.find_inverse = find_inverse
        BaseSearcher.__init__(self, editor, search_text)
    
    def __str__(self):
        return "disasm matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return text
    
    def get_matches(self, editor):
        matches = editor.disassembly.search(self.search_text, self.match_case)
        return matches

class CommentSearcher(BaseSearcher):
    pretty_name = "comments"

    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.match_case = match_case
        self.find_inverse = find_inverse
        BaseSearcher.__init__(self, editor, search_text)
    
    def __str__(self):
        return "comment matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return text
    
    def get_matches(self, editor):
        segment = editor.segment
        match_case = self.match_case
        s = segment.start_addr
        matches = []
        if match_case:
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

known_searchers = [
    HexSearcher,
    CharSearcher,
    DisassemblySearcher,
    CommentSearcher,
    ]
