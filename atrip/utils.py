import types
import uuid as stdlib_uuid

import numpy as np

from . import errors

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


def uuid():
    u = stdlib_uuid.uuid4()

    # Force it into a str type so it isn't serialized as something weird
    # through jsonpickle
    return str(u)


def to_numpy(value):
    if type(value) is np.ndarray:
        # force copy to make sure we aren't pointing to an immutable array
        return value.copy()
    elif type(value) is bytes:
        return np.copy(np.frombuffer(value, dtype=np.uint8))
    elif type(value) is list:
    	return np.asarray(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")


def to_numpy_list(value):
    if type(value) is np.ndarray:
        return value
    return np.asarray(value, dtype=np.uint32)


def text_to_int(text, default_base="hex"):
    """ Convert text to int, raising exeception on invalid input
    """
    if text.startswith("0x"):
        value = int(text[2:], 16)
    elif text.startswith("$"):
        value = int(text[1:], 16)
    elif text.startswith("#"):
        value = int(text[1:], 10)
    elif text.startswith("%"):
        value = int(text[1:], 2)
    else:
        if default_base == "dec":
            value = int(text)
        else:
            value = int(text, 16)
    return value


def bool_to_ranges(matches):
    w = np.where(matches == True)[0]
    # split into groups with consecutive numbers
    groups = np.split(w, np.where(np.diff(w) != 1)[0] + 1)
    ranges = []
    for group in groups:
        if np.alen(group) > 0:
            ranges.append((int(group[0]), int(group[-1]) + 1))
    return ranges


def collapse_values(src):
    """Given a list of integers, return a list of lists, where each entry
    contains a value and the start/end location of that value.

    For example, the list [0, 0, 0, 0, 255, 99, 99, 99] would return
    [
        [0, 0, 4],
        [255, 4, 5],
        [99, 5, 8],
    ]
    """
    d = to_numpy_list(src)
    changes = np.where(np.diff(d) > 0)[0]
    index = 0
    ranges = []
    for end in changes:
        end = end + 1
        ranges.append([int(d[index]), int(index), int(end)])
        index = end
    if index < len(d):
        ranges.append([int(d[index]), int(index), len(d)])
    return ranges


def restore_value_to_ranges(dest, ranges, value):
    """Restore a list given the description returned by `collapse_list`
    """
    for start, end in ranges:
        print(f"{hex(start)}:{hex(end)} = {value}")
        dest[start:end] = value


def restore_values(dest, ranges):
    """Restore a list given the description returned by `collapse_list`
    """
    for value, start, end in ranges:
        dest[start:end] = value


def collapse_to_ranges(src, compact=False):
    """Given a list of integers, return a list of lists that represent groups
    of monotonically increasing integers.

    For example, the list [0, 1, 2, 3, 4, 5, 7, 10, 11, 99, 500, 501, 502, 892]
    would return:

    [
        [0, 6],
        [7, 8],
        [10, 12],
        [99, 100],
        [500, 503],
        [892, 893],
    ]

    Note that ranges are returned in python slice notation; that is, the 2nd
    entry is one beyond the end value.

    if compact is True, one element ranges are stored as a single integer, so
    the above example would instead produce:

    [
        [0, 6],
        7,
        [10, 12],
        99,
        [500, 503],
        892,
    ]

    potentially saving space if there are a large number of entries with no
    neighbors.
    """
    groups = np.split(src, np.where(np.diff(src) != 1)[0] + 1)
    ranges = []
    for group in groups:
        if np.alen(group) > 0:
            start = int(group[0])
            end = int(group[-1]) + 1
            if compact and end == start + 1:
                ranges.append(start)
            else:
                ranges.append([start, end])
    return ranges


def restore_from_ranges(dest, ranges):
    index = 0
    for item in ranges:
        try:
            single = int(item)
        except TypeError:
            start, end = item
            count = end - start
            dest[index:index + count] = np.arange(start, end, dtype=np.uint32)
        else:
            count = 1
            dest[index:index + count] = single
        index += count
