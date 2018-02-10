# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
import omnivore.framework.clipboard as clipboard
from omnivore.utils.file_guess import FileMetadata
from omnivore.utils.wx.multisash import MultiSash
from omnivore8bit.arch.machine import Machine, Atari800
from omnivore8bit.document import SegmentedDocument
from omnivore8bit.utils.segmentutil import SegmentData, DefaultSegment, AnticFontSegment
from omnivore.utils.processutil import run_detach

from commands import PasteCommand
from linked_base import LinkedBase

import logging
log = logging.getLogger(__name__)


class DummyLinkedBase(object):
    segment = None
    segment_number = 0

class DummyFocusedViewer(object):
    linked_base = DummyLinkedBase


class ByteEditor(FrameworkEditor):
    """ The toolkit specific implementation of a ByteEditor.  See the
    IByteEditor interface for the API documentation.
    """

    #### 'IPythonEditor' interface ############################################

    obj = Instance(File)

    #### traits

    task_arguments = Str

    grid_range_selected = Bool

    emulator_label = Unicode("Run Emulator")

#    segment_parser_label = Property(Unicode)
    segment_parser_label = Unicode("whatever")

    initial_segment = Any(None)

    initial_font_segment = Any(None)

    ### View traits

    can_copy_baseline = Bool

    can_trace = Bool(False)

    can_resize_document = Bool(False)

    has_origin = Bool(False)

    center_base = Instance(LinkedBase)

    focused_viewer = Any(None)  # should be Instance(SegmentViewer), but creates circular imports

    linked_bases = List(LinkedBase)

    viewers = List(Any)

    #### Events ####

    changed = Event

    focused_viewer_changed_event = Event

    key_pressed = Event(KeyPressedEvent)

    # Class attributes (not traits)

    rect_select = False

    pane_creation_count = 0

    default_viewers = "hex,bitmap,char,disassembly"

    #### trait default values

    def _style_default(self):
        return np.zeros(len(self), dtype=np.uint8)

    def _segments_default(self):
        r = SegmentData(self.bytes,self.style)
        return list([DefaultSegment(r, 0)])

    def _program_memory_map_default(self):
        return dict()

    def _focused_viewer_default(self):
        return DummyFocusedViewer()

    #### trait property getters

    def _get_segment_parser_label(self):
        return self.document.segment_parser.menu_name if self.document is not None else "<parser type>"

    # Convenience functions

    @property
    def segment(self):
        return self.focused_viewer.linked_base.segment

    @property
    def linked_base(self):
        return self.focused_viewer.linked_base

    @property
    def segment_number(self):
        return self.focused_viewer.linked_base.segment_number

    @property
    def section_name(self):
        return str(self.segment)


    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def create(self, parent):
        SegmentedDocument.init_emulators(self)
        Machine.one_time_init(self)
        self.control = self._create_control(parent)
        self.task.emulator_changed = self.document

    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'initial segment' in e:
            self.initial_segment = e['initial segment']
        if 'diff highlight' in e:
            self.diff_highlight = bool(e['diff highlight'])

        layout = e.get('layout', {})

        viewer_metadata = {}
        for v in e.get('viewers', []):
            viewer_metadata[v['uuid']] = v

        log.debug("task arguments: '%s'" % self.task_arguments)
        if self.task_arguments or not viewer_metadata:
            names = self.task_arguments if self.task_arguments else self.default_viewers
            log.debug("overriding viewers: %s" % str(names))
            viewer_metadata = {}  # reset to start from empty if task args are specified
            for viewer_name in names.split(","):
                viewer_metadata[viewer_name.strip()] = {}

            layout = {}  # empty layout so it isn't cluttered with unused windows

        linked_bases = {}
        for b in e.get('linked bases', []):
            base = LinkedBase(editor=self)
            base.from_metadata_dict(b)
            linked_bases[base.uuid] = base
        self.create_viewers(layout, viewer_metadata, e, linked_bases)
        self.task.machine_menu_changed = self.focused_viewer.machine
        self.focused_viewer_changed_event = self.focused_viewer

    def to_metadata_dict(self, mdict, document):
        mdict["diff highlight"] = self.diff_highlight
        mdict["layout"] = self.control.get_layout()
        mdict["viewers"] = []
        bases = []
        for v in self.viewers:
            bases.append(v.linked_base)
            e = {"linked base": v.linked_base.uuid}
            v.to_metadata_dict(e, document)
            mdict["viewers"].append(e)
        mdict["linked bases"] = []
        for b in bases:
            e = {}
            b.to_metadata_dict(e, document)
            mdict["linked bases"].append(e)
        mdict["focused viewer"] = self.focused_viewer.uuid
        # if document == self.document:
        #     # If we're saving the document currently displayed, save the
        #     # display parameters too.
        #     mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper

    def rebuild_document_properties(self):
        log.debug("rebuilding document %s; intitial segment=%s" % (str(self.document), self.initial_segment))
        if not self.document.has_baseline:
            self.use_self_as_baseline(self.document)
        FrameworkEditor.rebuild_document_properties(self)
        self.focused_viewer.linked_base.find_segment(self.initial_segment)
        self.update_emulator()
        self.compare_to_baseline()
        self.can_resize_document = self.document.can_resize

    # def init_view_properties(self):
    #     if self.initial_font_segment:
    #         self.focused_viewer.linked_base.machine.change_font_data(self.initial_font_segment)

    def process_preference_change(self, prefs):
        log.debug("%s processing preferences change" % self.task.name)
        #self.machine.set_text_font(prefs.text_font)

    ##### Copy/paste

    @property
    def clipboard_data_format(self):
        return self.focused_viewer.clipboard_data_format

    def copy_selection_to_clipboard(self, name):
        return clipboard.set_from_selection(self.focused_viewer, name)

    def get_paste_data_from_clipboard(self):
        return clipboard.get_paste_data(self.focused_viewer)

    def process_paste_data(self, serialized_data, cmd_cls=None):
        if cmd_cls is None:
            cmd_cls = self.focused_viewer.get_paste_command(serialized_data)
        cmd = cmd_cls(self.segment, serialized_data)
        log.debug("processing paste object %s" % cmd)
        self.process_command(cmd)
        return cmd

    @property
    def supported_clipboard_data_objects(self):
        return self.focused_viewer.supported_clipboard_data_objects

    def select_all(self):
        self.focused_viewer.select_all()
        self.document.refresh_event = True

    def select_none(self):
        self.focused_viewer.select_none()
        self.document.refresh_event = True

    def select_invert(self):
        self.focused_viewer.select_invert()
        self.document.refresh_event = True

    def check_document_change(self):
        self.document.change_count += 1
        self.update_caret_history()

    def rebuild_ui(self):
        log.debug("rebuilding focused_base: %s" % str(self.focused_viewer.linked_base))
        self.document.recalc_event = True

    def refresh_panes(self):
        log.debug("refresh_panes called")

    def reconfigure_panes(self):
        self.update_pane_names()

    def update_pane_names(self):
        for viewer in self.viewers:
            viewer.update_caption()
        self.control.update_captions()

    @on_trait_change('document.emulator_change_event')
    def update_emulator(self):
        emu = self.document.emulator
        if emu is None:
            emu = self.document.get_system_default_emulator(self.task)
        if not self.document.is_known_emulator(emu):
            self.document.add_emulator(self.task, emu)
        self.emulator_label = "Run using '%s'" % emu['name']

    def run_emulator(self):
        emu = self.document.emulator
        if not emu:
            emu = self.document.get_system_default_emulator(self.task)
        if self.dirty:
            if not self.save():
                return
        exe = emu['exe']
        args = emu['args']
        fspath = self.document.filesystem_path()
        if fspath is not None:
            try:
                run_detach(exe, args, fspath, "%s")
            except RuntimeError, e:
                self.window.error("Failed launching %s %s\n\nError: %s" % (exe, args, str(e)), "%s Emulator Error" % emu['name'])
        else:
            self.window.error("Can't run emulator on:\n\n%s\n\nDocument is not on local filesystem" % self.document.uri, "%s Emulator Error" % emu['name'])

    def view_segment_number(self, number):
        self.focused_viewer.linked_base.view_segment_number(number)

    def get_extra_segment_savers(self, segment):
        savers = []
        for v in self.viewers:
            savers.extend(v.get_extra_segment_savers(segment))
        return savers

    def save_segment(self, saver, uri):
        try:
            bytes = saver.encode_data(self.segment, self)
            saver = lambda a,b: bytes
            self.document.save_to_uri(uri, self, saver, save_metadata=False)
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            #self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            raise

    def show_trace(self):
        """Highlight the current trace after switching to a new segment

        """
        if self.can_trace:
            self.disassembly.update_trace_in_segment()
            self.document.change_count += 1

    ##### Search

    def invalidate_search(self):
        self.task.change_minibuffer_editor(self)

    @property
    def searchers(self):
        search_order = []
        found = set()
        for v in self.viewers:
            for s in v.searchers:
                # searchers may depend on the viewer (like the disassembly)
                # or they may be generic to the segment
                if s.pretty_name not in found:
                    search_order.append(s)
                    found.add(s.pretty_name)
        log.debug("search order: %s" % [s.pretty_name for s in search_order])
        return search_order

    def compare_to_baseline(self):
        if self.diff_highlight and self.document.has_baseline:
            self.document.update_baseline()

    def get_label_at_index(self, index):
        return self.focused_viewer.linked_base.segment.label(index)

    def get_label_of_ranges(self, ranges):
        labels = []
        for start, end in ranges:
            if start > end:
                start, end = end, start
            labels.append("%s-%s" % (self.get_label_at_index(start), self.get_label_at_index(end - 1)))
        return ", ".join(labels)

    def get_label_of_first_byte(self, ranges):
        labels = []
        for start, end in ranges:
            if start > end:
                start, end = end, start
            labels.append(self.get_label_at_index(start))
        return ", ".join(labels)

    def get_selected_status_message(self):
        if not self.focused_viewer.linked_base.selected_ranges:
            return ""
        if len(self.focused_viewer.linked_base.selected_ranges) == 1:
            r = self.focused_viewer.linked_base.selected_ranges
            first = r[0][0]
            last = r[0][1]
            num = abs(last - first)
            if num == 1: # python style, 4:5 indicates a single byte
                return "[1 byte selected %s]" % self.get_label_of_ranges(r)
            elif num > 0:
                return "[%d bytes selected %s]" % (num, self.get_label_of_ranges(r))
        else:
            return "[%d ranges selected]" % (len(self.focused_viewer.linked_base.selected_ranges))

    def show_status_message(self, msg):
        s = self.get_selected_status_message()
        if s:
            msg = "%s %s" % (msg, s)
        self.task.status_bar.message = msg

    def add_user_segment(self, segment, update=True):
        self.document.add_user_segment(segment)
        self.added_segment(segment, update)

    def added_segment(self, segment, update=True):
        if update:
            self.update_segments_ui()
            if self.segment_list is not None:
                self.segment_list.ensure_visible(segment)
        self.metadata_dirty = True

    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
        self.update_segments_ui()
        self.metadata_dirty = True

    def update_segments_ui(self):
        # Note: via profiling, it turns out that this is a very heavyweight
        # call, producing hundreds of thousands of trait notifier events. This
        # should only be called when the number of segments or document has
        # changed. If only the segment being viewed is changed, just set the
        # task.segment_selected trait
        log.debug("update_segments_ui costs a lot of time!!!!!!")
        self.sidebar.recalc_active()
        if self.focused_viewer.linked_base.segment_parser is not None:
            self.segment_parser_label = self.focused_viewer.linked_base.segment_parser.menu_name
        else:
            self.segment_parser_label = "No parser"
        self.task.segments_changed = self.document.segments
        self.task.segment_selected = self.segment_number

    def find_in_user_segment(self, base_index):
        # FIXME: Profiling shows this as a big bottleneck when there are
        # comments. It inefficiently loops over segments, then the call to
        # get_index_from_base is super slow in atrcopy because of all the
        # calculations and dereferences needed to compute the index. That
        # probably needs to be cached.
        for s in self.document.user_segments:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        for s in self.document.segment_parser.segments[1:]:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        return None, None

    def do_popup(self, control, popup):
        # The popup event may happen on a control that isn't the focused
        # viewer, and the focused_viewer needs to point to that control for
        # actions to work in the correct viewer. The focus needs to be forced
        # to that control, we can't necessarily count on the ActivatePane call
        # to work before the popup.
        self.focused_viewer = control.segment_viewer
        ret = FrameworkEditor.do_popup(self, control, popup)
        wx.CallAfter(self.force_focus, control.segment_viewer)
        return ret

    def change_bytes(self, start, end, bytes, pretty=None):
        """Convenience function to perform a ChangeBytesCommand
        """
        self.document.change_count += 1
        cmd = CoalescingChangeByteCommand(self.segment, start, end, bytes)
        if pretty:
            cmd.pretty_name = pretty
        self.process_command(cmd)

    def popup_visible(self):
        log.debug("checking sidebar: popup visible? %s" % self.sidebar.control.has_popup())
        return self.sidebar.control.has_popup()

    def clear_popup(self):
        log.debug("clearing popup")
        self.sidebar.control.clear_popup()

    def add_viewer(self, viewer_cls, linked=True):
        center_viewer = self.viewers[0]
        center_base = center_viewer.linked_base
        viewer = viewer_cls.create(self.control, center_base)
        self.viewers.append(viewer)
        self.control.add(viewer.control, viewer.uuid)
        center_base.force_data_model_update()
        self.update_pane_names()

    ###########################################################################
    # Trait handlers.
    ###########################################################################

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        panel = MultiSash(parent)
        panel.Bind(MultiSash.EVT_CLIENT_ACTIVATED, self.on_viewer_active)
        panel.Bind(MultiSash.EVT_CLIENT_CLOSE, self.on_viewer_close)

        self.sidebar = self.window.get_dock_pane('byte_edit.sidebar')

        return panel

    def create_viewers(self, layout, viewer_metadata, default_viewer_metadata, linked_bases):
        # Create a set of viewers from a list
        log.debug("layout: %s" % layout)
        import pprint
        log.debug("viewer_metadata: %s" % str(viewer_metadata.keys()))

        center_base = LinkedBase(editor=self)
        # self.linked_bases.append(center_base)

        self.focused_viewer = None
        layer = 0
        viewers = viewer_metadata.keys()
        if layout:
            # try:
                print(layout)
                self.control.restore_layout(layout)
            # except ValueError:
            #     log.warning("Unable to decode layout")

        while self.focused_viewer is None:
            for uuid in viewers:
                log.debug("loading viewer: %s" % uuid)
                e = viewer_metadata[uuid]
                if e:
                    viewer_type = e['name']
                    linked_base = linked_bases[e['linked base']]
                    log.debug("recreating viewer %s: %s" % (viewer_type, uuid))
                else:  # either not a uuid or an unknown uuid
                    e = default_viewer_metadata
                    viewer_type = uuid  # try the value of 'uuid' as a viewer name
                    linked_base = center_base
                    uuid = None
                    log.debug("using default metadata for %s" % (viewer_type))

                try:
                    viewer_cls = self.task.find_viewer_by_name(viewer_type)
                except ValueError:
                    log.error("unknown viewer %s, uuid=%s" % (viewer_type, uuid))
                    continue
                log.debug("creating viewer %s (%s) with linked base %s" % (uuid, viewer_type, str(linked_base)))
                viewer = viewer_cls.create(self.control, linked_base, None, uuid)
                viewer.from_metadata_dict(e)
                log.debug("created viewer %s (%s)" % (viewer.uuid, viewer.name))

                self.viewers.append(viewer)
                if self.focused_viewer is None:
                    self.set_focused_viewer(viewer)
                if not self.control.replace_by_uuid(viewer.control, viewer.uuid):
                    log.debug("viewer %s not found, adding in new pane" % viewer.uuid)
                    self.control.add(viewer.control, viewer.uuid)

            if self.focused_viewer is None:
                # just load default hex editor if nothing has been created
                viewers = ['hex']
                first = False

        print str(self.control.get_layout())
        # if perspective:
        #     # The following creates a new pane_info based on the layout...
        #     self.mgr.LoadPerspective(perspective)

        #     # ...so we have to move this newly created pane_info back onto the
        #     # viewer
        #     for v in self.viewers:
        #         v.pane_info = self.mgr.GetPane(v.uuid)
        self.update_pane_names()

    #### wx event handlers

    def force_focus(self, viewer):
        self.focus_uuid(viewer.uuid)
        self.update_pane_names()
        viewer.update_toolbar()

    def set_focused_viewer(self, viewer):
        self.focused_viewer = viewer
        self.focused_viewer_changed_event = viewer
        self.caret_handler = viewer.linked_base
        viewer.linked_base.calc_action_enabled_flags()

    def on_viewer_active(self, evt):
        try:
            v = evt.child.segment_viewer
        except AttributeError:
            # must be an empty window (a multisash window that has no segment
            # viewer). It can be closed without any further action.
            pass
        else:
            v = evt.child.segment_viewer
            if v == self.focused_viewer:
                log.debug("on_pane_active: already current viewer %s" % v)
            else:
                log.debug("on_pane_active: activated viewer %s %s" % (v, v.window_title))
                self.set_focused_viewer(v)

    def on_viewer_close(self, evt):
        try:
            v = evt.child.segment_viewer
        except AttributeError:
            # must be an empty window (a multisash window that has no segment
            # viewer). It can be closed without any further action.
            pass
        else:
            log.debug("on_pane_close: closed viewer %s %s" % (v, v.window_title))
            self.viewers.remove(v)
