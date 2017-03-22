from traits.api import HasTraits, provides

from atrcopy import iter_parsers, SegmentData, UnsupportedDiskImage

from omnivore.file_type.i_file_recognizer import IFileRecognizer
from omnivore8bit.document import SegmentedDocument


@provides(IFileRecognizer)
class AtrcopyRecognizer(HasTraits):
    name = "Atrcopy Disk Image"

    id = "application/vnd.atrcopy"

    def identify(self, guess):
        r = SegmentData(guess.numpy)
        try:
            mime, parser = iter_parsers(r)
        except UnsupportedDiskImage:
            parser = None
        if parser is not None:
            guess.parser = parser
            return mime

    def load(self, guess):
        doc = SegmentedDocument(metadata=guess.metadata, bytes=guess.numpy)
        doc.set_segments(guess.parser)
        from omnivore8bit.utils.extra_metadata import check_builtin
        check_builtin(doc)
        return doc
