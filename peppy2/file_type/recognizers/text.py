from envisage.api import Plugin
from traits.api import HasTraits, provides, List

from peppy2.file_type.i_file_recognizer import IFileRecognizer
from peppy2.utils.textutil import guessBinary

@provides(IFileRecognizer)
class PlainTextRecognizer(HasTraits):
    """ Identify common text formats
    
    """
    id = "text/plain"
    
    def identify_bytes(self, byte_stream):
        """Return a MIME type if byte stream can be identified.
        
        If byte stream is not known, returns None
        """
        if not guessBinary(byte_stream):
            return "text/plain"


class TextRecognizerPlugin(Plugin):
    """ A plugin that contributes to the peppy.file_type.recognizer extension point. """

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy.file_type.recognizer.text'

    # The plugin's name (suitable for displaying to the user).
    name = 'Text Recognizer Plugin'

    # This tells us that the plugin contributes the value of this trait to the
    # 'greetings' extension point.
    recognizer = List([PlainTextRecognizer()], contributes_to='peppy2.file_recognizer')
