
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, on_trait_change, HasTraits, Undefined

from omnivore.framework.editor import FrameworkEditor
from ..byte_edit.linked_base import LinkedBase


import logging
log = logging.getLogger(__name__)


class SegmentViewer(HasTraits):
    """Base class for any viewer window that can display (& optionally edit)
    the data in a segment

    Linked base exists for the lifetime of the viewer. If the user wants to
    change the base, a new viewer is created and replaces this viewer.
    """
    editor = Instance(FrameworkEditor)

    linked_base = Instance(LinkedBase)

    control = Any(None)

    @classmethod
    def create_control(cls, parent, linked_base):
        raise NotImplementedError("Implement in subclass!")

    @classmethod
    def create(cls, parent, linked_base):
        control = cls.create_control(parent, linked_base)
        v = cls(linked_base=linked_base, control=control)
        control.segment_viewer = v
        return v

    @on_trait_change('linked_base.editor.document.recalc_event')
    def process_segment_change(self, evt):
        log.debug("process_segment_change for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        self.recalc_view()

    @on_trait_change('linked_base.ensure_visible_index')
    def process_ensure_visible(self, evt):
        log.debug("process_ensure_visible for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.control.set_cursor_index(evt.source_control, evt.index_visible, evt.cursor_column)

    @property
    def window_title(self):
        return "viewer"

    def recalc_view(self):
        """Rebuild the entire UI after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.recalc_view()

    @on_trait_change('linked_base.editor.document.refresh_event')
    def refresh_view(self):
        """Redraw the UI
        """
        self.control.refresh_view()

    def get_extra_segment_savers(self, segment):
        """Hook to provide additional ways to save the data based on this view
        of the data
        """
        return []

