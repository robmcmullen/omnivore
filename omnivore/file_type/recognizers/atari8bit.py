from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore.framework.document import Document
from omnivore.utils.segmentutil import guess_parser_for


@provides(IFileRecognizer)
class XEXRecognizer(HasTraits):
    name = "Atari 8-bit Executable"
    
    id = "application/vnd.atari8bit.xex"
    
    def identify(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        parser = guess_parser_for(self.id, doc)
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
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        parser = guess_parser_for(self.id, doc)
        if parser is not None:
            guess.parser = parser
            return self.id
    
    def load(self, guess):
        doc = Document(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        from omnivore.utils.extra_metadata import check_builtin
        check_builtin(doc)
        return doc
