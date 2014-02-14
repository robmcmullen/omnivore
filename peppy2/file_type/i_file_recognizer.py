# Enthought library imports.
from traits.api import Interface, Str

class IFileRecognizer(Interface):
    """ File type identifier service.
    
    """

    # The service name
    name = Str
    
    # The file type category, e.g. image, binary, archive, etc.
    category = Str

    def identify_bytes(self, byte_stream):
        """Return a MIME type if byte stream can be identified.
        
        If byte stream is not known, returns None
        """

class IFileRecognizerDriver(Interface):
    """ File type identifier service.
    
    """

    def recognize(self, guess):
        """Attempt to set the mime type of a FileGuess.
        """
