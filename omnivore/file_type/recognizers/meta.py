from traits.api import HasTraits, provides

from omnivore.file_type.i_file_recognizer import IFileRecognizer, RecognizerBase


@provides(IFileRecognizer)
class OmnivoreRecognizer(RecognizerBase):
    """Meta recognizer that forces the loading of a disk image when the
    .omnivore file is selected instead
    """

    name = "Omnivore Extra Metadata File"

    id = "text/vnd.omnivore.extra_metadata"

    before = "application/vnd.*"

    def identify(self, guess):
        uri = guess.metadata.uri
        if uri.endswith(".omnivore"):
            b = guess.bytes
            if b.startswith("#") or b.startswith("{"):
                uri = uri[0:-9]
                guess.reload(uri)
