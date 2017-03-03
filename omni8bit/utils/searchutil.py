import re


class BaseSearcher(object):
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
    def __str__(self):
        return "hex matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return bytearray.fromhex(text)

class CharSearcher(BaseSearcher):
    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.match_case = match_case
        self.find_inverse = find_inverse
        BaseSearcher.__init__(self, editor, search_text)
    
    def __str__(self):
        return "char matches: %s" % str(self.matches)

class DisassemblySearcher(BaseSearcher):
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

known_searchers = [
    HexSearcher,
    CharSearcher,
    DisassemblySearcher,
    ]
