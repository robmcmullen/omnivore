from traits.api import HasTraits, provides, List, Instance

from i_file_recognizer import IFileRecognizer

@provides(IFileRecognizer)
class FileRecognizerDriver(HasTraits):
    """ Identify common image formats
    
    """

    # The service name
    name = "Driver"
    
    # The file type category, e.g. image, executable, archive, etc.
    category = "driver"
    
    #####
    
    recognizers = List(Instance(IFileRecognizer))
    
    def identify_bytes(self, byte_stream):
        """Using the list of known recognizers, return a MIME type of a byte
        stream.
        """
        if byte_stream is None:
            return ""
        print "trying %d recognizers " % len(self.recognizers)
        for recognizer in self.recognizers:
            print "trying %s recognizer: ",
            mime = recognizer.identify_bytes(byte_stream)
            if mime is not None:
                print "found %s" % mime
                return mime
            print "unrecognized"
        return ""
