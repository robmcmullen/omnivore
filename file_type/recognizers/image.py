from envisage.api import Plugin
from traits.api import HasTraits, provides, List

from ..i_file_recognizer import IFileRecognizer
import imghdr

@provides(IFileRecognizer)
class ImageRecognizer(HasTraits):
    """ Identify common image formats
    
    """

    # The service name
    name = "Image"
    
    # The file type category, e.g. image, executable, archive, etc.
    category = "image"
    
    #####
    
    mime_map = {
        'rgb': 'x-rgb',
        'pbm': 'x-portable-bitmap',
        'pgm': 'x-portable-graymap',
        'ppm': 'x-portable-pixmap',
        'rast': 'x-cmu-raster',
        'xbm': 'x-xbitmap,'
        }
    
    def identify_bytes(self, byte_stream):
        """Return a MIME type if byte stream can be identified.
        
        If byte stream is not known, returns None
        """
        name = imghdr.what("", h=byte_stream)
        if name is None:
            return
        name = self.mime_map.get(name, name)
        return "image/%s" % name


class ImageRecognizerPlugin(Plugin):
    """ A plugin that contributes to the peppy.file_type.recognizer extension point. """

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy.file_type.recognizer.image'

    # The plugin's name (suitable for displaying to the user).
    name = 'Image Recognizer Plugin'

    # This tells us that the plugin contributes the value of this trait to the
    # 'greetings' extension point.
    recognizer = List([ImageRecognizer()], contributes_to='peppy.file_type.recognizer')
