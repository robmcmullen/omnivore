import logging
log = logging.getLogger(__name__)


class SimpleFrameworkError(RuntimeError):
    pass

class RecreateDynamicMenuBar(SimpleFrameworkError):
    pass

class EditorNotFound(SimpleFrameworkError):
    pass

class UnsupportedFileType(SimpleFrameworkError):
    pass

class ProgressCancelError(SimpleFrameworkError):
    pass

class DocumentError(SimpleFrameworkError):
    pass
