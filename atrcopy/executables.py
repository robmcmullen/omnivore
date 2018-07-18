import numpy as np

from . import errors
from .segments import SegmentData, EmptySegment, ObjSegment, RawSectorsSegment, DefaultSegment, SegmentedFileSegment, SegmentSaver, get_style_bits
from .utils import *

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


def get_xex(segments, run_addr=None):
    segments_copy = [s for s in segments]  # don't affect the original list!
    main_segment = None
    sub_segments = []
    data_style = get_style_bits(data=True)
    total = 2
    runad = False
    for s in segments:
        total += 4 + len(s)
        if s.origin == 0x2e0:
            runad = True
    if not runad:
        words = np.empty([1], dtype='<u2')
        if run_addr:
            found = False
            for s in segments:
                if run_addr >= s.origin and run_addr < s.origin + len(s):
                    found = True
                    break
            if not found:
                raise errors.InvalidBinaryFile("Run address points outside data segments")
        else:
            run_addr = segments[0].origin
        words[0] = run_addr
        r = SegmentData(words.view(dtype=np.uint8))
        s = DefaultSegment(r, 0x2e0)
        segments_copy[0:0] = [s]
        total += 6
    bytes = np.zeros([total], dtype=np.uint8)
    rawdata = SegmentData(bytes)
    main_segment = DefaultSegment(rawdata)
    main_segment.data[0:2] = 0xff  # FFFF header
    main_segment.style[0:2] = data_style
    i = 2
    for s in segments_copy:
        # create new sub-segment inside new main segment that duplicates the
        # original segment's data/style
        new_s = DefaultSegment(rawdata[i:i+4+len(s)], s.origin)
        words = new_s.data[0:4].view(dtype='<u2')
        words[0] = s.origin
        words[1] = s.origin + len(s) - 1
        new_s.style[0:4] = data_style
        new_s.data[4:4+len(s)] = s[:]
        new_s.style[4:4+len(s)] = s.style[:]
        i += 4 + len(s)
        new_s.copy_user_data(s, 4)
        sub_segments.append(new_s)
    return main_segment, sub_segments


def get_bsave(segments, run_addr=None):
    # Apple 2 executables get executed at the first address loaded. If the
    # run_addr is not the first byte of the combined data, have to create a
    # new 3-byte segment with a "JMP run_addr" to go at the beginning
    origin = 100000000
    last = -1

    for s in segments:
        origin = min(origin, s.origin)
        last = max(last, s.origin + len(s))
        if _xd: log.debug("contiguous bytes needed: %04x - %04x" % (origin, last))
    if run_addr and run_addr != origin:
        # check if run_addr points to some location that has data
        found = False
        for s in segments:
            if run_addr >= s.origin and run_addr < s.origin + len(s):
                found = True
                break
        if not found:
            raise errors.InvalidBinaryFile("Run address points outside data segments")
        origin -= 3
        hi, lo = divmod(run_addr, 256)
        raw = SegmentData([0x4c, lo, hi])
        all_segments = [DefaultSegment(raw, origin=origin)]
        all_segments.extend(segments)
    else:
        all_segments = segments
    size = last - origin
    image = np.zeros([size + 4], dtype=np.uint8)
    words = image[0:4].view(dtype="<u2")  # always little endian
    words[0] = origin
    words[1] = size
    for s in all_segments:
        index = s.origin - origin + 4
        print("setting data for $%04x - $%04x at index $%04x" % (s.origin, s.origin + len(s), index))
        image[index:index + len(s)] = s.data
    return image


def create_executable_file_data(filename, segments, run_addr=None):
    name = filename.lower()
    if name.endswith("xex"):
        base_segment, user_segments = get_xex(segments, run_addr)
        return base_segment.data, "XEX"
    elif name.endswith("bin") or name.endswith("bsave"):
        data = get_bsave(segments, run_addr)
        return data, "B"
    raise errors.UnsupportedContainer
