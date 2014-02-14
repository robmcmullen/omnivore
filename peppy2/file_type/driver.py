from traits.api import HasTraits, provides, List, Instance

from i_file_recognizer import IFileRecognizer, IFileRecognizerDriver

from peppy2.utils.textutil import guessBinary

@provides(IFileRecognizerDriver)
class FileRecognizerDriver(HasTraits):
    """ Identify files using the available FileRecognizer extension point contributors
    
    """
    
    #####
    
    recognizers = List(Instance(IFileRecognizer))
    
    def recognize(self, guess):
        """Using the list of known recognizers, attempt to set the MIME of a FileGuess
        """
        if guess.bytes is None:
            return
        print "trying %d recognizers " % len(self.recognizers)
        for recognizer in self.recognizers:
            print "trying %s recognizer: " % recognizer.name,
            mime = recognizer.identify_bytes(guess.bytes)
            if mime is not None:
                print "found %s" % mime
                guess.metadata.mime = mime
                return
            print "unrecognized"
        
        if guessBinary(guess.bytes):
            mime = "application/octet-stream"
        else:
            mime = "text/plain"
        print "Not matched by any registered recognizers; bytes look like %s" % mime
        guess.metadata.mime = mime
