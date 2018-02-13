import wx
import numpy as np

from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges

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

class ClipboardError(RuntimeError):
    pass


hex_format = True

def format_number(num):
    if hex_format:
        return "$%x" % num
    else:
        return "%d" % num


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


class ClipboardSerializer(object):
    data_format_name = "_base_"
    pretty_name = "_base_"

    @classmethod
    def get_composite_object(cls, raw_data, serialized_data, data_format_name=""):
        """Create a composite data object that holds both the serialized data
        and a hexified string of the raw data that can be pasted into other
        applications
        """
        if data_format_name:
            name = data_format_name
        else:
            name = cls.data_format_name
        data_obj = wx.CustomDataObject(name)
        data_obj.SetData(serialized_data)
        text = " ".join(["%02x" % i for i in raw_data])
        text_obj = wx.TextDataObject()
        text_obj.SetText(text)
        c = wx.DataObjectComposite()
        c.Add(data_obj)
        c.Add(text_obj)
        return c

    @classmethod
    def selection_to_data_object(cls, viewer):
        raise NotImplementedError("Unimplemented for data format %s" % cls.data_format_name)

    @classmethod
    def from_data_object(cls, data_obj):
        try:
            d = data_obj.GetObject(fmt)
        except AttributeError:
            d = data_obj
        return d


    def __init__(self, source_data_format_name):
        self.source_data_format_name = source_data_format_name
        self.data = None
        self.ranges = []
        self.carets = None
        self.indexes = None
        self.style = None
        self.comment_indexes = None
        self.comments = None
        self.num_rows = None
        self.num_columns = None
        self.items_per_row = None

    @property
    def size_info(self):
        size = np.alen(self.data)
        return "%s bytes" % (format_number(size))

    @property
    def summary(self):
        """Return a string with a summary of the contents of the data object
        """
        return self.size_info

    def unpack_data_object(self, viewer, data_obj):
        """Parse the data object into the instance attributes
        """
        raise NotImplementedError("Unimplemented for data format %s" % cls.data_format_name)

    def unpack_metadata(self, viewer):
        """Parse the data object into the class attributes
        """
        raise NotImplementedError("Unimplemented for data format %s" % cls.data_format_name)


class TextSelection(ClipboardSerializer):
    data_format_name = "text"
    pretty_name = "Text"

    @property
    def summary(self):
        """Return a string with a summary of the contents of the data object
        """
        return "%s text characters" % (format_number(np.alen(self.data)))

    def unpack_data_object(self, viewer, data_obj):
        fmts = data_obj.GetAllFormats()
        if wx.DF_TEXT in fmts:
            value = data_obj.GetText().encode('utf-8')
        elif wx.DF_UNICODETEXT in fmts:  # for windows
            value = data_obj.GetText().encode('utf-8')
        else:
            raise ClipboardError("Unsupported format type for %s: %s" % (self.data_format_name, ", ".join([str(f) in fmts])))
        self.data = np.fromstring(value, dtype=np.uint8)
        self.carets = viewer.linked_base.carets.copy()


class BinarySelection(ClipboardSerializer):
    data_format_name = "numpy"
    pretty_name = "Single Selection"

    @classmethod
    def selection_to_data_object(cls, viewer):
        # NOTE: also handles multiple selection
        ranges, indexes = viewer.get_selected_ranges_and_indexes()
        log.debug("selection_to_data_object: viewer=%s ranges=%s indexes=%s" % (viewer, ranges, indexes))
        if len(ranges) > 0:
            metadata = viewer.get_selected_index_metadata(indexes)
            log.debug("  metadata: %s" % str(metadata))
            if len(ranges) == 1:
                r = ranges[0]
                data = viewer.segment[r[0]:r[1]]
                s1 = data.tostring()
                serialized = "%d,%s%s" % (len(s1), s1, metadata)
                name = ""
            elif np.alen(indexes) > 0:
                data = viewer.segment[indexes]
                s1 = data.tostring()
                s2 = indexes.tostring()
                serialized = "%d,%d,%s%s%s" % (len(s1), len(s2), s1, s2, metadata)
                name = "numpy,multiple"
            else:
                raise ClipboardError("No ranges or indexes selected")
            return cls.get_composite_object(data, serialized, name)
        else:
            return None

    def unpack_data_object(self, viewer, data_obj):
        value = get_data_object_value(data_obj, self.data_format_name)
        len1, value = value.split(",", 1)
        len1 = int(len1)
        value, j = value[0:len1], value[len1:]
        self.data = np.fromstring(value, dtype=np.uint8)
        self.style, self.comment_indexes, self.comments = viewer.restore_selected_index_metadata(j)
        self.carets = viewer.linked_base.carets.copy()


class MultipleBinarySelection(ClipboardSerializer):
    data_format_name = "numpy,multiple"
    pretty_name = "Multiple Selection"

    @property
    def summary(self):
        """Return a string with a summary of the contents of the data object
        """
        return "%s in multiple ranges" % (self.size_info)

    def unpack_data_object(self, viewer, data_obj):
        value = get_data_object_value(data_obj, self.data_format_name)
        len1, len2, value = value.split(",", 2)
        len1 = int(len1)
        len2 = int(len2)
        split1 = len1
        split2 = len1 + len2
        value, index_string, j = value[0:split1], value[split1:split2], value[split2:]
        self.data = np.fromstring(value, dtype=np.uint8)
        self.indexes = np.fromstring(index_string, dtype=np.uint32)
        self.style, self.comment_indexes, self.comments = viewer.restore_selected_index_metadata(j)
        self.carets = viewer.linked_base.carets.copy()


class RectangularSelection(ClipboardSerializer):
    data_format_name = "numpy,columns"
    pretty_name = "Rectangular Selection"

    @classmethod
    def selection_to_data_object(cls, viewer):
        if viewer.linked_base.anchor_start_index != viewer.linked_base.anchor_end_index:
            anchor_start, anchor_end, (r1, c1), (r2, c2) = viewer.control.get_highlight_indexes()
            bpr = viewer.control.items_per_row
            last = r2 * bpr
            d = viewer.segment[:last].reshape(-1, bpr)
            data = d[r1:r2, c1:c2]
            return cls.get_composite_object(data.flat, "%d,%d,%s" % (r2 - r1, c2 - c1, data.tostring()))
        return None

    @property
    def summary(self):
        """Return a string with a summary of the contents of the data object
        """
        return "%s bytes in %sx%s rectangle" % (self.size_info, format_number(self.num_columns), format_number(self.num_rows))

    def unpack_data_object(self, viewer, data_obj):
        value = get_data_object_value(data_obj, self.data_format_name)
        r, c, value = value.split(",", 2)
        self.num_rows = int(r)
        self.num_columns = int(c)
        self.data = np.fromstring(value, dtype=np.uint8)
        self.carets = viewer.linked_base.carets.copy()
        self.items_per_row = viewer.control.items_per_row


def create_data_object(viewer, name):
    try:
        serializer_cls = known_clipboard_serializers[name]
    except IndexError:
        raise ClipboardError("Unknown format name %s" % name)
    log.debug("create_data_object: viewer=%s name=%s" % (viewer, name))
    data_obj = serializer_cls.selection_to_data_object(viewer)
    if data_obj is None:
        raise ClipboardError("Viewer %s can't encode as a %s." % (viewer, serializer.pretty_name.lower()))

    # format may not be the same as requested because the type of selection
    # (single, multiple, etc.) may result in a different format.
    fmt = data_obj.GetPreferredFormat()
    name = fmt.GetId()
    try:
        serializer_cls = known_clipboard_serializers[name]
    except IndexError:
        raise ClipboardError("Unknown format name %s" % name)
    serializer = serializer_cls(name)
    serializer.unpack_data_object(viewer, data_obj)
    log.debug("create_data_object: serialized: %s" % serializer)
    return data_obj, serializer


def set_from_selection(viewer, name):
    data_obj, serializer = create_data_object(viewer, name)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(data_obj)
        wx.TheClipboard.Close()
        return serializer
    else:
        raise ClipboardError("System error: unable to open clipboard")


def get_paste_data_object(viewer):
    data_objs = viewer.supported_clipboard_data_objects

    if wx.TheClipboard.Open():
        for data_obj in data_objs:
            success = wx.TheClipboard.GetData(data_obj)
            if success:
                break
        wx.TheClipboard.Close()
    else:
        raise ClipboardError("Unable to open clipboard")
    return data_obj


def get_paste_data(viewer):
    data_obj = get_paste_data_object(viewer)
    if wx.DF_TEXT in data_obj.GetAllFormats() or wx.DF_UNICODETEXT in data_obj.GetAllFormats():  # for windows
        serializer_cls = TextSelection
    else:
        fmt = data_obj.GetPreferredFormat()
        name = fmt.GetId()
        try:
            serializer_cls = known_clipboard_serializers[name]
        except IndexError:
            raise ClipboardError("Unknown format name %s" % name)
    serializer = serializer_cls(name)
    serializer.unpack_data_object(viewer, data_obj)
    return serializer

known_clipboard_serializers = {}
for s in [TextSelection, BinarySelection, MultipleBinarySelection, RectangularSelection]:
    known_clipboard_serializers[s.data_format_name] = s
