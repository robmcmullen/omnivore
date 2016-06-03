from traits.api import HasTraits, provides

from atrcopy import guess_parser_for_system, SegmentData

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import Document


@provides(IFileRecognizer)
class AtariRecognizer(HasTraits):
    name = "Atari 8-bit Disk Image"
    
    id = "application/vnd.atari8bit"
    
    def identify(self, guess):
        r = SegmentData(guess.numpy)
        mime, parser = guess_parser_for_system(self.id, r)
        if parser is not None:
            guess.parser = parser
            return mime
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        from omnivore.utils.extra_metadata import check_builtin
        check_builtin(doc)
        return doc
