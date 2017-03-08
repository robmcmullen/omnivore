from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import BaseDocument

from omnivore_extra.crypto.utils.permute import PermutePrivate


@provides(IFileRecognizer)
class PrivateTextRecognizer(HasTraits):
    """Recognizer for pound bang style executable script files
    
    """
    id = "text/private"
    
    before = "text/poundbang"

    header = "#!omnivore-private\n"
    
    def identify(self, guess):
        byte_stream = guess.get_utf8()
        if not byte_stream.startswith(self.header):
            return
        return self.id
    
    def load(self, guess):
        start = len(self.header)
        doc = BaseDocument(metadata=guess.metadata, bytes=guess.numpy[start:])
        doc.permute = PermutePrivate()
        print "loading %s: %s" % (self.id, doc)
        return doc
