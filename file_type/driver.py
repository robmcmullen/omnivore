from traits.api import HasTraits, provides, List, Instance

from i_file_recognizer import IFileRecognizer, IFileRecognizerDriver

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
            print "trying %s recognizer: ",
            mime = recognizer.identify_bytes(guess.bytes)
            if mime is not None:
                print "found %s" % mime
                guess.metadata.mime = mime
            print "unrecognized"
