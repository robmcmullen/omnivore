from traits.api import HasTraits, provides, List, Instance

from peppy2.utils.sortutil import before_after_wildcard_sort

from i_file_recognizer import IFileRecognizer, IFileRecognizerDriver

@provides(IFileRecognizerDriver)
class FileRecognizerDriver(HasTraits):
    """ Identify files using the available FileRecognizer extension point contributors
    
    """
    
    recognizers = List(Instance(IFileRecognizer))
    
    def recognize(self, guess):
        """Using the list of known recognizers, attempt to set the MIME of a FileGuess
        """
        if guess.bytes is None:
            return
        print "trying %d recognizers " % len(self.recognizers)
        for recognizer in self.recognizers:
            print "trying %s recognizer: " % recognizer.id,
            mime = recognizer.identify(guess)
            if mime is not None:
                print "found %s" % mime
                guess.metadata.mime = mime
                return
            print "unrecognized"
        
        guess.metadata.mime = "application/octet-stream"
        print "Not recognized; default is %s" % guess.metadata.mime

    def _recognizers_changed(self, old, new):
        print "_recognizers_changed: old=%s new=%s" % (str(old), str(new))
        print "  old order: %s" % ", ".join([r.id for r in self.recognizers])
        s = before_after_wildcard_sort(self.recognizers)
        # Is there a proper way to set the value in the trait change callback?
        # Assigning a new list will get call the notification handler multiple
        # times, although it seems to end the cycle when it detects that the
        # list items haven't changed from the last time.  I'm working around
        # this by replacing the items in the list so that the list object
        # itself hasn't changed, only the members.
        self.recognizers[:] = s
        print "  new order: %s" % ", ".join([r.id for r in s])
