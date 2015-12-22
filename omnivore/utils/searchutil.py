import re


class HexSearcher(object):
    def __init__(self, editor, search_text, **kwargs):
        self.search_text = self.get_search_text(search_text)
        self.matches = self.get_matches(editor)
    
    def __str__(self):
        return "hex matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return bytearray.fromhex(text)
    
    def get_matches(self, editor):
        text = editor.segment.search_copy
        rs = re.escape(str(self.search_text))
        matches = [(i.start(), i.end()) for i in re.finditer(rs, text)]
        return matches

class CharSearcher(object):
    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.search_text = self.get_search_text(search_text)
        self.match_case = match_case
        self.find_inverse = find_inverse
        self.matches = self.get_matches(editor)
    
    def __str__(self):
        return "char matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return bytearray(text, "utf-8")
    
    def get_matches(self, editor):
        text = editor.segment.search_copy
        rs = re.escape(str(self.search_text))
        matches = [(i.start(), i.end()) for i in re.finditer(rs, text)]
        return matches

class DisassemblySearcher(object):
    def __init__(self, editor, search_text, match_case=False, find_inverse=True, **kwargs):
        self.editor = editor
        self.search_text = self.get_search_text(search_text)
        self.match_case = match_case
        self.find_inverse = find_inverse
        self.matches = self.get_matches(editor)
    
    def __str__(self):
        return "disasm matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return text
    
    def get_matches(self, editor):
        matches = self.editor.disassembly.search(self.search_text, self.match_case)
        return matches

known_searchers = [
    HexSearcher,
    CharSearcher,
    DisassemblySearcher,
    ]
