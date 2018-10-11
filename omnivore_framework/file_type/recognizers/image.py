from traits.api import HasTraits, provides

from omnivore_framework.file_type.i_file_recognizer import IFileRecognizer, RecognizerBase
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

    def can_load_mime(self, mime):
        for name in self.mime_map.values():
            if mime == "image/%s" % name:
                return True
        return False

    def identify(self, guess):
        name = imghdr.what("", h=guess.get_bytes())
        if name is None:
            return
        name = self.mime_map.get(name, name)
        return "image/%s" % name
