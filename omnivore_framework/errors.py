import logging
log = logging.getLogger(__name__)


class SimpleFrameworkError(RuntimeError):
    pass

class RecreateDynamicMenuBar(SimpleFrameworkError):
    pass

class EditorNotFound(SimpleFrameworkError):
    pass
