import wx
import numpy as np
import jsonpickle

from sawx.errors import ClipboardError
from sawx.clipboard import calc_composite_object

from atrip import Segment
from atrip.stringifier import find_stringifier_by_name

import logging
log = logging.getLogger(__name__)


# Full list of valid data formats:
#
# >>> import wx
# >>> [x for x in dir(wx) if x.startswith("DF_")]
# ['DF_BITMAP', 'DF_DIB', 'DF_DIF', 'DF_ENHMETAFILE', 'DF_FILENAME', 'DF_HTML',
# 'DF_INVALID', 'DF_LOCALE', 'DF_MAX', 'DF_METAFILE', 'DF_OEMTEXT',
# 'DF_PALETTE', 'DF_PENDATA', 'DF_PRIVATE', 'DF_RIFF', 'DF_SYLK', 'DF_TEXT',
# 'DF_TIFF', 'DF_UNICODETEXT', 'DF_WAVE']


def get_data_object_by_format(data_obj, fmt):
    # First try a composite object, then simple: have to handle both
    # cases
    try:
        d = data_obj.GetObject(fmt)
    except AttributeError:
        d = data_obj
    return d


def get_data_object_value(data_obj, name):
    # First try a composite object, then simple: have to handle both
    # cases
    try:
        fmt = data_obj.GetFormat()
    except AttributeError:
        fmt = data_obj.GetPreferredFormat()
    if fmt.GetId() == name:
        d = get_data_object_by_format(data_obj, fmt)
        return d.GetData().tobytes()
    raise ClipboardError("Expecting %s data object, found %s" % (name, fmt.GetId()))


def create_numpy_clipboard_blob(ranges, indexes, segment, control):
    print(ranges)
    rects = control.get_rects_from_selections()
    if rects:
        blob = NumpyRectBlob(ranges, indexes, rects, segment, control)
    else:
        if len(ranges) == 1:
            blob = NumpyBlob(ranges, indexes, segment, control)
        elif len(ranges) > 1:
            blob = NumpyMultipleBlob(ranges, indexes, segment, control)
    return blob


class ClipboardBlob:
    data_format_name = "_base_"
    ui_name = "_base_"

    def __init__(self):
        self.data = None
        self.indexes = None
        self.style = None
        self.relative_comment_indexes = None
        self.comments = None
        self.num_rows = None
        self.num_cols = None
        self.num_regions = 1
        self.dest_items_per_row = None
        self.dest_carets = None

    @property
    def serialized(self):
        return jsonpickle.encode(self).encode('utf-8')

    @property
    def data_obj(self):
        data_obj = wx.CustomDataObject(self.data_format_name)
        data_obj.SetData(self.serialized)
        return data_obj

    def text_data_obj(self, stringifier="hexify"):
        try:
            s = find_stringifier_by_name(stringifier)
            log.warning(f"Stringifier {stringifier} not found; using default")
        except KeyError:
            s = find_stringifier_by_name("hexify")
        text = s.calc_text(self.data)
        text_obj = wx.TextDataObject()
        text_obj.SetText(text)
        return text_obj


class TextBlob(ClipboardBlob):
    """Supports unpacking data objects only."""
    data_format_name = "text"
    ui_name = "Text"

    def __init__(self, data_obj):
        super().__init()
        self.unpack_data_object(data_obj)

    def unpack_data_object(self, viewer, data_obj):
        fmts = data_obj.GetAllFormats()
        if wx.DF_TEXT in fmts:
            value = data_obj.GetText().encode('utf-8')
        elif wx.DF_UNICODETEXT in fmts:  # for windows
            value = data_obj.GetText().encode('utf-8')
        else:
            raise ClipboardError("Unsupported format type for %s: %s" % (self.data_format_name, ", ".join([str(f) in fmts])))
        self.data = np.fromstring(value, dtype=np.uint8)
        self.dest_carets = viewer.control.caret_handler.copy()


class NumpyBlob(ClipboardBlob):
    data_format_name = "numpy"
    ui_name = "Single Selection"

    def __init__(self, ranges, indexes, segment, control):
        super().__init__()
        self.ranges = ranges
        self.num_regions = len(self.ranges)
        self.indexes = indexes
        self.get_data_from_segment(segment, control)
        self.style, self.relative_comment_indexes, self.comments = segment.calc_selected_index_metadata(indexes)

    def get_data_from_segment(self, segment, control):
        r = self.ranges[0]
        self.data = segment[r[0]:r[1]]


class NumpyMultipleBlob(NumpyBlob):
    data_format_name = "numpy,multiple"
    ui_name = "Multiple Selection"

    def get_data_from_segment(self, segment, control):
        self.data = segment[self.indexes]


class NumpyRectBlob(NumpyMultipleBlob):
    def __init__(self, ranges, indexes, rects, segment, control):
        super().__init__(ranges, indexes, segment, control)
        self.get_rects_from_segment(rects, segment, control)

    def get_rects_from_segment(self, rects, segment, control):
        r = rects[0]  # FIXME: handle multiple rects
        self.num_rows, self.num_cols, self.data = control.get_data_from_rect(r)


def parse_data_obj(data_obj, viewer):
    if wx.DF_TEXT in data_obj.GetAllFormats() or wx.DF_UNICODETEXT in data_obj.GetAllFormats():  # for windows
        blob = TextBlob(data_obj)
    else:
        fmt = data_obj.GetPreferredFormat()
        name = fmt.GetId()
        value = get_data_object_value(data_obj, name)
        try:
            blob = jsonpickle.decode(value.decode('utf-8'))
            print("DECODED BLOB!", blob)
        except IndexError:
            raise ClipboardError(f"Failed unpacking data_obj {name}: {value}")
    blob.dest_carets = viewer.control.caret_handler.copy()
    return blob
