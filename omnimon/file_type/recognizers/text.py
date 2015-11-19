from traits.api import HasTraits, provides

from omnimon.file_type.i_file_recognizer import IFileRecognizer
from omnimon.utils.textutil import guessBinary

@provides(IFileRecognizer)
class PlainTextRecognizer(HasTraits):
    """Default plain text identifier based on percentage of non-ASCII bytes.
    
    """
    id = "text/plain"
    
    def identify(self, guess):
        if not guessBinary(guess.get_utf8()):
            return "text/plain"

@provides(IFileRecognizer)
class XMLTextRecognizer(HasTraits):
    """Default plain text identifier based on percentage of non-ASCII bytes.
    
    """
    id = "text/xml"
    
    before = "text/plain"
    
    def identify(self, guess):
        byte_stream = guess.get_utf8().strip()
        if not byte_stream.startswith("<"):
            return
        if byte_stream.startswith("<?xml"):
            found_xml = True
        else:
            found_xml = False
        if "<rss" in byte_stream:
            return "application/rss+xml"
        byte_stream = byte_stream.lower()
        if "<!doctype html" in byte_stream or "<html" in byte_stream:
            return "text/html"
        
        if found_xml:
            return "text/xml"

@provides(IFileRecognizer)
class PoundBangTextRecognizer(HasTraits):
    """Recognizer for pound bang style executable script files
    
    """
    id = "text/poundbang"
    
    before = "text/plain"
    
    def identify(self, guess):
        byte_stream = guess.get_utf8()
        if not byte_stream.startswith("#!"):
            return
        line = byte_stream[2:80].lower().strip()
        if line.startswith("/usr/bin/env"):
            line = line[12:].strip()
        words = line.split()
        names = words[0].split("/")
        if names[-1]:
            return "text/%s" % names[-1]
