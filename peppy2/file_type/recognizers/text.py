from traits.api import HasTraits, provides

from peppy2.file_type.i_file_recognizer import IFileRecognizer
from peppy2.utils.textutil import guessBinary

@provides(IFileRecognizer)
class PlainTextRecognizer(HasTraits):
    """Default plain text identifier based on percentage of non-ASCII bytes.
    
    """
    id = "text/plain"
    
    def identify_bytes(self, byte_stream):
        """Return a MIME type if byte stream can be identified.
        
        If byte stream is not known, returns None
        """
        if not guessBinary(byte_stream):
            return "text/plain"

@provides(IFileRecognizer)
class PoundBangTextRecognizer(HasTraits):
    """Recognizer for pound bang style executable script files
    
    """
    id = "text/poundbang"
    
    before = "text/plain"
    
    def identify_bytes(self, byte_stream):
        """Return a MIME type if byte stream can be identified.
        
        If byte stream is not known, returns None
        """
        if not byte_stream.startswith("#!"):
            return
        line = byte_stream[2:80].lower().strip()
        if line.startswith("/usr/bin/env"):
            line = line[12:].strip()
        words = line.split()
        names = words[0].split("/")
        if names[-1]:
            return "text/%s" % names[-1]
