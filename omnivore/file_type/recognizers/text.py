from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer, RecognizerBase
from omnivore.utils.textutil import guessBinary


@provides(IFileRecognizer)
class PlainTextRecognizer(RecognizerBase):
    """Default plain text identifier based on percentage of non-ASCII bytes.
    
    """
    id = "text/plain"

    def identify(self, guess):
        if not guessBinary(guess.get_bytes()):
            return "text/plain"


@provides(IFileRecognizer)
class XMLTextRecognizer(RecognizerBase):
    """Default plain text identifier based on percentage of non-ASCII bytes.
    
    """
    id = "text/xml"

    before = "text/plain"

    def can_load_mime(self, mime):
        return mime == "text/xml" or mime == "text/html"

    def identify(self, guess):
        byte_stream = guess.get_bytes().strip()
        if not byte_stream.startswith(b"<"):
            return
        if byte_stream.startswith(b"<?xml"):
            found_xml = True
        else:
            found_xml = False
        if b"<rss" in byte_stream:
            return "application/rss+xml"
        byte_stream = byte_stream.lower()
        if b"<!doctype html" in byte_stream or b"<html" in byte_stream:
            return "text/html"

        if found_xml:
            return "text/xml"


@provides(IFileRecognizer)
class PoundBangTextRecognizer(RecognizerBase):
    """Recognizer for pound bang style executable script files
    
    """
    id = "text/poundbang"

    before = "text/plain"

    def identify(self, guess):
        byte_stream = guess.get_bytes()
        if not byte_stream.startswith(b"#!"):
            return
        line = byte_stream[2:80].lower().strip()
        if line.startswith(b"/usr/bin/env"):
            line = line[12:].strip()
        words = line.split()
        names = words[0].split("/")
        if names[-1]:
            return "text/%s" % names[-1]
