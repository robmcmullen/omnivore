from traits.api import HasTraits, provides

from i_filetype import IFileType
import imghdr

@provides(IFileType)
class ImageFileType(HasTraits):
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
        if byte_stream is None:
            return
        name = imghdr.what("", h=byte_stream)
        if name is None:
            return
        name = self.mime_map.get(name, name)
        return "image/%s" % name
