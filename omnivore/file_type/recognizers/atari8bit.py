from traits.api import HasTraits, provides

from atrcopy import guess_parser_for, SegmentData

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import Document


@provides(IFileRecognizer)
class XEXRecognizer(HasTraits):
    name = "Atari 8-bit Executable"
    
    id = "application/vnd.atari8bit.xex"
    
    def identify(self, guess):
        r = SegmentData(guess.numpy)
        parser = guess_parser_for(self.id, r)
        if parser is not None:
            guess.parser = parser
            return self.id
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        from omnivore.utils.extra_metadata import check_builtin
        check_builtin(doc)
        return doc


@provides(IFileRecognizer)
class ATRRecognizer(HasTraits):
    name = "Atari 8-bit Disk Image"
    
    id = "application/vnd.atari8bit.atr"
    
    def identify(self, guess):
        r = SegmentData(guess.numpy)
        parser = guess_parser_for(self.id, r)
        if parser is not None:
            guess.parser = parser
            return self.id
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        from omnivore.utils.extra_metadata import check_builtin
        check_builtin(doc)
        return doc
