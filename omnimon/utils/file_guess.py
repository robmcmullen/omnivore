import os
from traits.api import HasTraits, Str, Unicode


class FileMetadata(HasTraits):
    uri = Unicode
    
    mime = Str(default="application/octet-stream")
    
    def __str__(self):
        return "uri=%s, mime=%s" % (self.uri, self.mime)


class FileGuess(object):
    """Loads the first part of a file and provides a container for metadata

    """
    # Arbitrary size header, but should be large enough that binary files can
    # be scanned for a signature
    head_size = 1024*1024
    
    def __init__(self, uri):
        fh = open(uri, "rb")
        
        # In order to handle arbitrarily sized files, only read the first
        # header bytes.  If the file is bigger, it will be read by the task
        # as needed.
        self.bytes = fh.read(self.head_size)
        fh.close()
        
        # Use the default mime type until it is recognized
        self.metadata = FileMetadata(uri=uri)
        
    def __str__(self):
        return "guess: metadata: %s, %d bytes available for signature" % (self.metadata, len(self.bytes))
    
    def get_utf8(self):
        return self.bytes
    
    def get_metadata(self):
        return self.metadata.clone_traits()

    def get_stream(self):
        fh = open(self.metadata.uri, "rb")
        return fh
