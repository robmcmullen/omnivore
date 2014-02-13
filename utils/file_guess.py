import os
from traits.api import HasTraits, Str, Unicode


class FileMetadata(HasTraits):
    uri = Unicode
    
    mime = Str(default="application/octet-stream")


class FileGuess(object):
    """Loads the first part of a file and tries to guess its MIME type

    """
    # Arbitrary size header, but should be large enough that binary files can
    # be scanned for a signature
    head_size = 1024*1024
    
    def __init__(self, uri, mime_service):
        fh = open(uri, "rb")
        
        # In order to handle arbitrarily sized files, only read the first
        # header bytes.  If the file is bigger, it will be read by the task
        # as needed.
        self.bytes = fh.read(self.head_size)
        fh.close()
        mime = mime_service.identify_bytes(self.bytes)
        print mime
        
        self.metadata = FileMetadata(uri=uri, mime=mime)
        
    def get_utf8(self):
        return self.bytes
    
    def get_metadata(self):
        return self.metadata.clone_traits()

    def get_stream(self):
        fh = open(self.metadata.uri, "rb")
        return fh
