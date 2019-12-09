import pkg_resources

import numpy as np

import logging
log = logging.getLogger(__name__)


_signatures = None

def _find_signatures():
    signatures = []
    for entry_point in pkg_resources.iter_entry_points('atrip.signatures'):
        mod = entry_point.load()
        log.debug(f"find_signatures: Found module {entry_point.name}={mod.__name__}")
        if hasattr(mod, "sha1_signatures"):
            signatures.append(mod)
    return signatures

def find_signatures():
    global _signatures

    if _signatures is None:
        _signatures = _find_signatures()
    return _signatures


class Signature:
    def __init__(self, mime, name):
        self.mime = mime
        self.name = name

    def __str__(self):
        return f"{self.mime}: {self.name}"


def guess_signature_from_container(container, verbose=False):
    found = None
    sha_hash = container.sha1
    log.debug(f"container: {container}; sha1={sha_hash}")
    for mod in find_signatures():
        for mime, sigs in mod.sha1_signatures.items():
            try:
                name = sigs[sha_hash]
            except KeyError:
                continue
            else:
                log.debug(f"found match: {name}")
                return Signature(mime, name)
    else:
        log.debug(f"no match found in sha1 signature database")
    return None


# different than the above mime_parse_order, this list is the order in which
# the mime parsers will appear in a UI. Some, like the vectrex and atari2600
# parsers, aren't included in the parse order because they will identify
# many things incorrectly. They are used only when parsing by size and
# signature.
mime_display_order = [
    "application/x.atari8bit.atr",
    "application/x.atari8bit.xex",
    "application/x.atari8bit.cart",
    "application/x.atari5200.cart",
    "application/x.atari2600.cart",
    "application/x.atari2600.starpath",
    "application/x.vectrex",
    "application/x.mame_rom",
    "application/x.apple2.dsk",
    "application/x.apple2.bin",
    "application/x.rom",
    ]

pretty_mime = {
    "application/x.atari8bit.atr": "Atari 8-bit Disk Image",
    "application/x.atari8bit.xex": "Atari 8-bit Executable",
    "application/x.atari8bit.cart": "Atari 8-bit Cartridge",
    "application/x.atari5200.cart": "Atari 5200 Cartridge",
    "application/x.atari2600.cart": "Atari 2600 Cartridge",
    "application/x.atari2600.starpath": "Atari 2600 Starpath Cassette",
    "application/x.vectrex": "GCE Vectrex Cartridge",
    "application/x.mame_rom": "MAME",
    "application/x.rom": "ROM Image",
    "application/x.apple2.dsk": "Apple ][ Disk Image",
    "application/x.apple2.bin": "Apple ][ Binary",
}
