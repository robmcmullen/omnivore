import logging
log = logging.getLogger(__name__)


class SawxError(RuntimeError):
    pass

class RecreateDynamicMenuBar(SawxError):
    pass

class ProcessKeystrokeNormally(SawxError):
    pass

class EditorNotFound(SawxError):
    pass

class UnsupportedFileType(SawxError):
    pass

class ProgressCancelError(SawxError):
    pass

class DocumentError(SawxError):
    pass

class MissingDocumentationError(SawxError):
    pass

class ClipboardError(SawxError):
    pass

class ReadOnlyFilesystemError(SawxError):
    pass
