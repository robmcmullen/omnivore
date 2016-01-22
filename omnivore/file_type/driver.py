from traits.api import HasTraits, provides, List, Instance

from omnivore.utils.sortutil import before_after_wildcard_sort
from omnivore.framework.document import Document

from i_file_recognizer import IFileRecognizer, IFileRecognizerDriver

import logging
log = logging.getLogger(__name__)

@provides(IFileRecognizerDriver)
class FileRecognizerDriver(HasTraits):
    """ Identify files using the available FileRecognizer extension point contributors
    
    """
    
    recognizers = List(Instance(IFileRecognizer))
    
    def recognize(self, guess):
        """Using the list of known recognizers, attempt to set the MIME of a FileGuess
        """
        if guess.bytes is None:
            return Document(metadata=guess.metadata, bytes="")
        
        document = None
        log.debug("trying %d recognizers " % len(self.recognizers))
        for recognizer in self.recognizers:
            log.debug("trying %s recognizer: " % recognizer.id,)
            mime = recognizer.identify(guess)
            if mime is not None:
                guess.metadata.mime = mime
                log.info("found %s for %s" % (mime, guess.metadata.uri))
                try:
                    document = recognizer.load(guess)
                except AttributeError:
                    document = None
                break
        
        if mime is None:
            guess.metadata.mime = "application/octet-stream"
            log.info("Not recognized; default is %s" % guess.metadata.mime)
        if document is None:
            document = Document(metadata=guess.metadata, bytes=guess.numpy)
        return document

    def _recognizers_changed(self, old, new):
        log.debug("_recognizers_changed: old=%s new=%s" % (str(old), str(new)))
        log.debug("  old order: %s" % ", ".join([r.id for r in self.recognizers]))
        s = before_after_wildcard_sort(self.recognizers)
        # Is there a proper way to set the value in the trait change callback?
        # Assigning a new list will get call the notification handler multiple
        # times, although it seems to end the cycle when it detects that the
        # list items haven't changed from the last time.  I'm working around
        # this by replacing the items in the list so that the list object
        # itself hasn't changed, only the members.
        self.recognizers[:] = s
        log.debug("  new order: %s" % ", ".join([r.id for r in s]))
