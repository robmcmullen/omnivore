import uuid

import wx
import wx.lib.agw.aui as aui

from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined
from envisage.api import ExtensionPoint

from omnivore.framework.plugin import FrameworkPlugin
from ..byte_edit.linked_base import LinkedBase
from omnivore.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges

from omnivore8bit.arch.machine import Machine, Atari800
from omnivore8bit.utils import searchutil

import logging
log = logging.getLogger(__name__)


class SegmentViewer(HasTraits):
    """Base class for any viewer window that can display (& optionally edit)
    the data in a segment

    Linked base exists for the lifetime of the viewer. If the user wants to
    change the base, a new viewer is created and replaces this viewer.
    """
    ##### class attributes

    name = "_base_"

    pretty_name = "_base_"

    has_bitmap = False

    has_font = False

    has_cpu = False

    has_hex = False

    has_metadata_only = False

    valid_mouse_modes = []  # toolbar description

    copy_special = []  # additional copy functions available when viewer is present

    searchers = [  # BaseSearcher classes that are applicable to this viewer
        searchutil.HexSearcher,
        searchutil.CommentSearcher,
    ]

    ##### Traits

    uuid = Str

    linked_base = Instance(LinkedBase)

    machine = Instance(Machine)

    control = Any(None)

    pane_info = Any(None)

    range_processor = Property(Any, depends_on='control')

    #### Default traits

    def _uuid_default(self):
        return str(uuid.uuid4())

    def _machine_default(self):
        return Atari800.clone_machine()

    ##### Properties

    @property
    def segment(self):
        return self.linked_base.segment

    @property
    def editor(self):
        return self.linked_base.editor

    ##### Class methods

    @classmethod
    def create_control(cls, parent, linked_base):
        raise NotImplementedError("Implement in subclass!")

    @classmethod
    def check_name(cls, name):
        return name == cls.name

    @classmethod
    def create(cls, parent, linked_base, machine=None, uuid=None):
        control = cls.create_control(parent, linked_base)
        v = cls(linked_base=linked_base, control=control)
        if machine is not None:
            v.machine = machine
        control.segment_viewer = v
        if uuid:
            v.uuid = uuid
        v.pane_info = aui.AuiPaneInfo().Name(v.uuid)
        v.create_post()
        return v

    ##### Cleanup

    def prepare_for_destroy(self):
        self.control.segment_viewer = None
        self.control = None

    ##### Initialization and serialization

    def create_post(self):
        # hook for subclasses to do some extra init
        pass

    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'uuid' in e:
            self.uuid = e['uuid']

        # FIXME: deprecated stuff?
        if 'machine mime' in e:
            mime = e['machine mime']
            if not mime.startswith(self.machine.mime_prefix):
                m = self.machine.find_machine_by_mime(mime)
                if m is not None:
                    self.machine = m
        if 'font' in e or 'font renderer' in e or 'font order' in e:
            if 'font renderer' in e or 'font order' in e:
                self.machine.set_font(e['font'], e.get('font renderer', None), e.get('font order', None))
            else:
                self.machine.set_font(e['font'][0], e['font'][1])

        if 'machine' in e:
            self.machine.restore_extra_from_dict(e['machine'])
        self.from_metadata_dict_post(e)

    def from_metadata_dict_post(self, e):
        # placeholder for subclasses to check for extra metadata
        pass

    def to_metadata_dict(self, mdict, document):
        mdict['name'] = self.name
        mdict['uuid'] = self.uuid
        mdict['linked base'] = self.linked_base.uuid
        mdict['machine'] = {}
        self.machine.serialize_extra_to_dict(mdict['machine'])
        self.to_metadata_dict_post(mdict, document)

    def to_metadata_dict_post(self, mdict, document):
        # placeholder for subclasses to check for extra metadata
        pass

    def set_machine(self, machine):
        self.machine = machine
        self.reconfigure_panes()

    ##### Range operations

    def _get_range_processor(self):  # Trait property getter
        return ranges_to_indexes

    def get_optimized_selected_ranges(self, ranges):
        return collapse_overlapping_ranges(ranges)

    ##### SegmentViewer interface

    def update_caption(self):
        if self.pane_info is not None:
            self.pane_info.Caption(self.window_title)

    @on_trait_change('linked_base.editor.document.data_model_changed')
    def process_data_model_change(self, evt):
        log.debug("process_data_model_change for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_data_model()

    @on_trait_change('linked_base.editor.document.recalc_event')
    def process_recalc_view(self, evt):
        log.debug("process_recalc_view for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.recalc_view()

    @on_trait_change('linked_base.ensure_visible_index')
    def process_ensure_visible(self, evt):
        log.debug("process_ensure_visible for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            if evt.dont_move_cursor == self.control:
                self.control.refresh_view()
            elif evt.source_control != self.control:
                self.show_cursor(evt.source_control, evt.index_visible, evt.cursor_column)
            else:
                log.debug("SKIPPED %s because it's the source control" % (self.control))

    @on_trait_change('linked_base.update_cursor')
    def process_update_cursor(self, evt):
        log.debug("process_update_cursor for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            control, index, bit = evt
            if control != self.control:
                self.show_cursor(control, index, bit)
            else:
                log.debug("SKIPPED %s because it's the source control" % (self.control))

    @on_trait_change('machine.font_change_event,machine.bitmap_shape_change_event,machine.bitmap_color_change_event,machine.disassembler_change_event')
    def machine_metadata_changed(self, evt):
        log.debug("machine_metadata_changed: %s evt=%s" % (self, str(evt)))
        if self.linked_base is not None:
            self.update_caption()
            self.linked_base.editor.update_pane_names()

    @property
    def window_title(self):
        return self.pretty_name

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        pass

    def recalc_view(self):
        """Rebuild the entire UI after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    def show_cursor(self, control, index, bit):
        self.control.set_cursor_index(control, index, bit)

    @on_trait_change('linked_base.editor.document.refresh_event')
    def refresh_view(self, evt):
        """Redraw the UI
        """
        log.debug("process_refresh_view for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.refresh_view()

    def get_extra_segment_savers(self, segment):
        """Hook to provide additional ways to save the data based on this view
        of the data
        """
        return []

    ##### toolbar

    def update_toolbar(self):
        pass

    ##### view settings

    @property
    def width(self):
        return self.control.bytes_per_row

    def set_width(self, width):
        self.control.bytes_per_row = self.validate_width(width)
        wx.CallAfter(self.control.recalc_view)

    def validate_width(self, width):
        return width

    @property
    def zoom(self):
        return self.control.zoom

    def set_zoom(self, zoom):
        self.control.zoom = zoom
        wx.CallAfter(self.control.recalc_view)

    ##### Selections

    def highlight_selected_ranges(self):
        s = self.linked_base.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges(self.linked_base.editor.selected_ranges, selected=True)

    def create_clipboard_data_object(self):
        e = self.linked_base.editor
        ranges, indexes = e.get_selected_ranges_and_indexes()
        metadata = e.get_selected_index_metadata(indexes)
        if len(ranges) == 1:
            r = ranges[0]
            data = e.segment[r[0]:r[1]]
            s1 = data.tostring()
            metadata = e.get_selected_index_metadata(indexes)
            data_obj = wx.CustomDataObject("numpy")
            s = "%d,%s%s" % (len(s1), s1, metadata)
            data_obj.SetData(s)
        elif np.alen(indexes) > 0:
            data = e.segment[indexes]
            s1 = data.tostring()
            s2 = indexes.tostring()
            metadata = e.get_selected_index_metadata(indexes)
            data_obj = wx.CustomDataObject("numpy,multiple")
            s = "%d,%d,%s%s%s" % (len(s1), len(s2), s1, s2, metadata)
            data_obj.SetData(s)
        else:
            data_obj = None
        if data_obj is not None:
            text = " ".join(["%02x" % i for i in data])
            text_obj = wx.TextDataObject()
            text_obj.SetText(text)
            c = wx.DataObjectComposite()
            c.Add(data_obj)
            c.Add(text_obj)
            return c
        return None

    def process_paste_data(self, extra, bytes, cmd_cls=None):
        # Byte editor handles normal numpy and numpy,multiple data. If viewers
        # can handle other types of paste data objects, handle it here. Return
        # True if handled, False if the viewer can't handle it.
        return False

    ##### Spring tab (pull out menu) interface

    def __call__(self, parent, task, **kwargs):
        control = self.create(parent, task.active_editor.focused_viewer.linked_base)
        return control

    def activate_spring_tab(self):
        self.recalc_view()


class ByteViewersPlugin(FrameworkPlugin):
    """ Plugin containing all the viewers for byte data
    """

    # Extension point IDs.
    VIEWERS = 'omnivore8bit.viewers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore8bit.viewer.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'Omnivore Byte Viewers'

    #### Contributions to extension points made by this plugin ################

    viewers = List(contributes_to=VIEWERS)

    segment_viewers = ExtensionPoint(
        List(Instance(SegmentViewer)), id="omnivore8bit.viewers", desc="A list of SegmentViewers that can display the data in a segment"
    )

    def _viewers_default(self):
        from omnivore8bit.viewers.bitmap import BitmapViewer, MemoryMapViewer
        from omnivore8bit.viewers.char import CharViewer
        from omnivore8bit.viewers.cpu import DisassemblyViewer
        from omnivore8bit.viewers.hex import HexEditViewer
        from omnivore8bit.viewers.info import CommentsViewer, UndoViewer, SegmentListViewer
        from omnivore8bit.viewers.map import MapViewer
        from omnivore8bit.viewers.tile import TileViewer
        from omnivore8bit.viewers.jumpman import JumpmanViewer

        return [BitmapViewer, CharViewer, DisassemblyViewer, HexEditViewer, MemoryMapViewer, CommentsViewer, UndoViewer, SegmentListViewer, MapViewer, TileViewer, JumpmanViewer]

plugins = [ByteViewersPlugin()]
