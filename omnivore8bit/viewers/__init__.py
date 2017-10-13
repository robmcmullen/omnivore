import uuid

import wx.lib.agw.aui as aui

from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined
from envisage.api import ExtensionPoint

from omnivore.framework.plugin import FrameworkPlugin
from ..byte_edit.linked_base import LinkedBase

from omnivore8bit.arch.machine import Machine

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

    ##### Traits

    linked_base = Instance(LinkedBase)

    machine = Instance(Machine)

    control = Any(None)

    pane_info = Any(None)

    @classmethod
    def create_control(cls, parent, linked_base):
        raise NotImplementedError("Implement in subclass!")

    @classmethod
    def get_aui_pane_name(cls):
        return "%s--%s" % (cls.name, str(uuid.uuid4()))

    @classmethod
    def create(cls, parent, linked_base, machine=None):
        control = cls.create_control(parent, linked_base)
        if machine is None:
            machine = linked_base.machine.clone_machine()
        v = cls(linked_base=linked_base, control=control, machine=machine)
        control.segment_viewer = v
        v.pane_info = aui.AuiPaneInfo().Name(cls.get_aui_pane_name())
        return v

    def update_caption(self):
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
            if evt.source_control != self.control:
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

    ##### Selections

    def highlight_selected_ranges(self):
        s = self.linked_base.segment
        s.clear_style_bits(selected=True)
        s.set_style_ranges(self.linked_base.editor.selected_ranges, selected=True)

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

        return [BitmapViewer, CharViewer, DisassemblyViewer, HexEditViewer, MemoryMapViewer, CommentsViewer, UndoViewer, SegmentListViewer, MapViewer]

plugins = [ByteViewersPlugin()]
