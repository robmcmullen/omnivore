import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

known_assemblers = []
default_assembler = None

try:
    from .pyatasm import ATasm
    known_assemblers.append(ATasm)
    if default_assembler is None:
        default_assembler = ATasm
except ImportError as e:
    log.warning(f"atasm (MAC/65) assembler not available: {e}")

from .. import errors
from .assembler_base import AssemblerBase, AssemblerResult

def find_assembler(assembler_name):
    for e in known_assemblers:
        if e.name == assembler_name or e == assembler_name:
            return e
    raise errors.UnknownAssemblerError("Unknown assembler '%s'" % assembler_name)
