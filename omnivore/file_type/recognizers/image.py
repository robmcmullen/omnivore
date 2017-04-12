from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer, RecognizerBase
import imghdr


@provides(IFileRecognizer)
class ImageRecognizer(RecognizerBase):
    """Recognizer for common image formats
    
    """
    id = "image/common"

    before = "text/plain"

    mime_map = {
        'rgb': 'x-rgb',
        'pbm': 'x-portable-bitmap',
        'pgm': 'x-portable-graymap',
        'ppm': 'x-portable-pixmap',
        'rast': 'x-cmu-raster',
        'xbm': 'x-xbitmap,'
        }

    def identify(self, guess):
        name = imghdr.what("", h=guess.get_utf8())
        if name is None:
            return
        name = self.mime_map.get(name, name)
        return "image/%s" % name
