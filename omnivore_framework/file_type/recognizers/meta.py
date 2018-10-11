from traits.api import HasTraits, provides

from omnivore_framework.file_type.i_file_recognizer import IFileRecognizer, RecognizerBase


@provides(IFileRecognizer)
class OmnivoreRecognizer(RecognizerBase):
    """Meta recognizer that forces the loading of a disk image when the
    .omnivore file is selected instead
    """

    name = "Omnivore Extra Metadata File"

    id = "text/vnd.omnivore_framework.extra_metadata"

    before = "application/vnd.*"

    def identify(self, guess):
        uri = guess.metadata.uri
        if uri.endswith(".omnivore"):
            b = guess.raw_bytes
            if b.startswith(b"#") or b.startswith(b"{"):
                uri = uri[0:-9]
                guess.reload(uri)
