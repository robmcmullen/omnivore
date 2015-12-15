from fs.opener import opener, fsopen

from traits.api import HasTraits, Str, Unicode

import logging
log = logging.getLogger(__name__)


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
        log.debug("Attempting to load %s" % uri)
        if uri.startswith("file://"):
            # FIXME: workaround to allow opening of file:// URLs with the
            # ! character
            uri = uri.replace("file://", "")
        fs, relpath = opener.parse(uri)
        log.debug("Filesystem: %s" % fs)
        fh = fs.open(relpath, "rb")
        
        # In order to handle arbitrarily sized files, only read the first
        # header bytes.  If the file is bigger, it will be read by the task
        # as needed.
        self.bytes = fh.read(self.head_size)
        fh.close()
        
        # Normalize the uri if possible
        if fs.haspathurl(relpath):
            uri = fs.getpathurl(relpath)
        elif fs.hassyspath(relpath):
            abspath = fs.getsyspath(relpath)
            if abspath.startswith("\\\\?\\") and len(abspath) < 260:
                # on windows, pyfilesystem returns extended path notation to
                # allow paths greater than 256 characters.  If the path is
                # short, change slashes to normal and remove the prefix
                abspath = abspath[4:].replace("\\", "/")
            uri = "file://" + abspath
        
        # Use the default mime type until it is recognized
        self.metadata = FileMetadata(uri=uri)
        
        # Release filesystem resources
        fs.close()
        
    def __str__(self):
        return "guess: metadata: %s, %d bytes available for signature" % (self.metadata, len(self.bytes))
    
    def get_utf8(self):
        return self.bytes
    
    def get_metadata(self):
        return self.metadata.clone_traits()

    def get_stream(self):
        fh = fsopen(self.metadata.uri, "rb")
        return fh
