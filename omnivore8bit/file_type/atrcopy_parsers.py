from traits.api import HasTraits, provides

from atrcopy import iter_parsers, guess_parser_for_mime, SegmentData, errors

from omnivore_framework.file_type.i_file_recognizer import IFileRecognizer
from ..document import SegmentedDocument
from .. import emulators as emu


@provides(IFileRecognizer)
class AtrcopyRecognizer(HasTraits):
    name = "Atrcopy Disk Image"

    id = "application/vnd.atrcopy"

    def can_load_mime(self, mime):
        return guess_parser_for_mime(mime) is not None

    def identify(self, guess):
        r = SegmentData(guess.numpy)
        try:
            mime, parser = iter_parsers(r)
        except errors.UnsupportedDiskImage:
            parser = None
        if parser is not None:
            guess.parser = parser
            return mime

    def load(self, guess):
        file_metadata = guess.json_metadata.get(".omniemu", {})
        emulator_type = file_metadata.get("emulator_type", None)
        if emulator_type:
            doc = emu.EmulationDocument(source_document=None, emulator_type=emulator_type)
        else:
            doc = SegmentedDocument(metadata=guess.metadata, raw_bytes=guess.numpy)
        doc.load_metadata(guess)
        return doc
