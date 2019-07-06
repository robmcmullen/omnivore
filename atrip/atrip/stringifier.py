import os
import inspect
import pkg_resources

from . import errors

import logging
log = logging.getLogger(__name__)


class Stringifier:
    """Stringifier (pretty printer) for data.

    Converts data to and from a human-readable representation.

    Stringifiers are stateless, but are implemented as normal classes for
    convenience and ease of subclassing.
    """
    text_type = None
    ui_name = "_base_"

    def __init__(self, byte_data=None):
        if byte_data is not None:
            self.text = self.calc_text(byte_data)

    def __str__(self):
        return self.text_type

    #### stringification

    def calc_text(self, byte_data):
        """Convert byte values into a string using this algorithm.

        `byte_data` must be a byte array or something that can pose for a byte
        array.

        If the data can't be losslessly represented by this stringifier, raise
        an `InvalidAlgorithm` exception. The caller must recognize this and
        take appropriate action.

        Subclasses should raise the `UnsupportedAlgorithm` exception if
        stringification is not implemented.
        """
        raise errors.UnsupportedAlgorithm(f"Stringifier '{self.text_type}' not implemented")

    #### parse

    def calc_byte_data(self, text_data):
        """Parse text using this stringifier's format.

        An `InvalidAlgorithm` exception will be raised if the text can't be
        parsed using this method.

        Subclasses should raise the `UnsupportedAlgorithm` exception if
        parsing is not implemented.
        """
        raise errors.UnsupportedAlgorithm(f"Parser '{self.text_type}' not implemented")


class ReprStringifier(Stringifier):
    text_type = "repr"
    ui_name = "Escaped String"

    def calc_text(self, byte_data):
        text = repr(byte_data)  # will generate byte string
        q = text[1]
        text = text[2:-1]  # remove 'b' and leading/trailing quotes
        if q == "'":
            # double quotes are literal, single quotes are escaped
            text = text.replace('"', "\\x22").replace("\\'", "\\x27")
        else:
            # single quotes are literal, double are escaped
            text = text.replace("'", "\\x27").replace('\\"', "\\x22")
        return text


_stringifiers = None

def _find_stringifiers():
    stringifiers = []
    for entry_point in pkg_resources.iter_entry_points('atrip.stringifiers'):
        mod = entry_point.load()
        log.debug(f"find_stringifier: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Stringifier in obj.__mro__[1:]:
                log.debug(f"find_stringifiers:   found stringifier class {name}")
                stringifiers.append(obj)
    stringifiers.append(ReprStringifier)
    return stringifiers

def find_stringifiers():
    global _stringifiers

    if _stringifiers is None:
        _stringifiers = _find_stringifiers()
    return _stringifiers

def find_stringifier_by_name(name):
    items = find_stringifiers()
    for c in items:
        if c.text_type == name:
            return c()
    raise KeyError(f"Unknown stringifier {name}")
