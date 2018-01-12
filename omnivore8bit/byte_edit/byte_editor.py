# Standard library imports.
import sys
import os

# Major package imports.
import wx
import wx.lib.agw.aui as aui
import numpy as np
import json

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
import omnivore.framework.clipboard as clipboard
from omnivore.utils.file_guess import FileMetadata
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

    # This is a flag to help set the cursor to the center row when the cursor
    # is moved in a different editor. Some editors can't use SetFocus inside an
    # event handler, so the focus could still be set on one editor even though
    # the user clicked on another. This results in the first editor not getting
    # centered unless this flag is checked also.
    pending_focus = Any(None)  # Flag to help

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
    def segment_number(self):
        return self.focused_viewer.linked_base.segment_number

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def document_length(self):
        return len(self.segment)


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

        log.debug("task arguments: '%s'" % self.task_arguments)
        if self.task_arguments:
            layout = self.task_arguments
        elif 'layout' in e:
            layout = e['layout']
        else:
            layout = self.default_viewers
        viewer_metadata = {'default': e}
        for v in e.get('viewers', []):
            viewer_metadata[v['uuid']] = v
        linked_bases = {}
        for b in e.get('linked bases', []):
            base = LinkedBase(editor=self)
            base.from_metadata_dict(b)
            linked_bases[base.uuid] = base
        self.create_viewers(layout, viewer_metadata, linked_bases)
        self.task.machine_menu_changed = self.focused_viewer.machine
        self.focused_viewer_changed_event = self.focused_viewer

    def to_metadata_dict(self, mdict, document):
        mdict["diff highlight"] = self.diff_highlight
        mdict["layout"] = self.mgr.SavePerspective()
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

    def get_numpy_from_data_object(self, data_obj):
        # Full list of valid data formats:
        #
        # >>> import wx
        # >>> [x for x in dir(wx) if x.startswith("DF_")]
        # ['DF_BITMAP', 'DF_DIB', 'DF_DIF', 'DF_ENHMETAFILE', 'DF_FILENAME',
        # 'DF_HTML', 'DF_INVALID', 'DF_LOCALE', 'DF_MAX', 'DF_METAFILE',
        # 'DF_OEMTEXT', 'DF_PALETTE', 'DF_PENDATA', 'DF_PRIVATE', 'DF_RIFF',
        # 'DF_SYLK', 'DF_TEXT', 'DF_TIFF', 'DF_UNICODETEXT', 'DF_WAVE']
        extra = None
        if wx.DF_TEXT in data_obj.GetAllFormats():
            value = data_obj.GetText().encode('utf-8')
        elif wx.DF_UNICODETEXT in data_obj.GetAllFormats():  # for windows
            value = data_obj.GetText().encode('utf-8')
        else:
            value = data_obj.GetData().tobytes()
            fmt = data_obj.GetPreferredFormat()
            if fmt.GetId() == "numpy,columns":
                r, c, value = value.split(",", 2)
                extra = fmt.GetId(), int(r), int(c)
            elif fmt.GetId() == "numpy":
                len1, value = value.split(",", 1)
                len1 = int(len1)
                value, j = value[0:len1], value[len1:]
                style, where_comments, comments = self.restore_selected_index_metadata(j)
                extra = fmt.GetId(), None, style, where_comments, comments
            elif fmt.GetId() == "numpy,multiple":
                len1, len2, value = value.split(",", 2)
                len1 = int(len1)
                len2 = int(len2)
                split1 = len1
                split2 = len1 + len2
                value, index_string, j = value[0:split1], value[split1:split2], value[split2:]
                indexes = np.fromstring(index_string, dtype=np.uint32)
                style, where_comments, comments = self.restore_selected_index_metadata(j)
                extra = fmt.GetId(), indexes, style, where_comments, comments
        bytes = np.fromstring(value, dtype=np.uint8)
        return bytes, extra

    @property
    def supported_clipboard_data_objects(self):
        return self.focused_viewer.supported_clipboard_data_objects

    def check_document_change(self):
        self.document.change_count += 1
        self.update_cursor_history()

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
        self.mgr.RefreshCaptions()

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
        viewer.pane_info.Right().Layer(10)
        self.viewers.append(viewer)
        self.mgr.AddPane(viewer.control, viewer.pane_info)
        center_base.force_data_model_update()
        self.update_pane_names()
        self.mgr.Update()

    def replace_center_viewer(self, viewer_cls):
        center_viewer = self.viewers[0]
        center_base = center_viewer.linked_base
        viewer = viewer_cls.create(self.control, center_base, center_viewer.machine)
        viewer.pane_info.CenterPane()

        center_viewer.prepare_for_destroy()
        self.mgr.ClosePane(center_viewer.pane_info)

        # Need to replace the first viewer here, because explicitly closing the
        # pane above doesn't trigger an AUI_PANE_CLOSE event
        self.viewers[0] = viewer
        log.debug("viewers after replacing center pane: %s" % str(self.viewers))
        self.mgr.AddPane(viewer.control, viewer.pane_info)
        center_base.force_data_model_update()
        self.mgr.Update()
        self.force_focus(viewer)

    ###########################################################################
    # Trait handlers.
    ###########################################################################

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        panel = wx.Panel(parent, style=wx.BORDER_NONE)

        # AUI Manager is the direct child of the task
        self.mgr = aui.AuiManager(agwFlags=aui.AUI_MGR_ALLOW_ACTIVE_PANE)
        art = self.mgr.GetArtProvider()
        art.SetMetric(aui.AUI_DOCKART_GRADIENT_TYPE, aui.AUI_GRADIENT_NONE)
        art.SetColor(aui.AUI_DOCKART_ACTIVE_CAPTION_COLOUR, art.GetColor(aui.AUI_DOCKART_ACTIVE_CAPTION_GRADIENT_COLOUR))
        panel.Bind(aui.framemanager.EVT_AUI_PANE_ACTIVATED, self.on_pane_active)
        panel.Bind(aui.framemanager.EVT_AUI_PANE_CLOSE, self.on_pane_close)

        # tell AuiManager to manage this frame
        self.mgr.SetManagedWindow(panel)

        self.sidebar = self.window.get_dock_pane('byte_edit.sidebar')

        return panel

    def create_viewers(self, layout, viewer_metadata, linked_bases):
        # Create a set of viewers from a list
        log.debug("layout: %s" % layout)

        center_base = LinkedBase(editor=self)
        # self.linked_bases.append(center_base)

        first = True
        self.focused_viewer = None
        layer = 0
        viewers = []
        perspective = ""
        if layout.startswith("layout2"):
            # it's a perspective string, so parse names out of it
            perspective = layout
            sections = layout.split("|")
            for section in sections[1:]:
                parts = section.split(";")[0].split("=")
                log.debug(str(parts))
                if parts[0] == "name":  # name is the uuid of the viewer
                    viewers.append(parts[1])
        if not viewers:
            # use default list of viewer names, not uuids, if there is no saved
            # layout.
            viewers = [a.strip() for a in layout.split(",")]


        while first:
            for uuid in viewers:
                if uuid in viewer_metadata:
                    e = viewer_metadata[uuid]
                    viewer_type = e['name']
                    linked_base = linked_bases[e['linked base']]
                else:  # either not a uuid or an unknown uuid
                    e = viewer_metadata.get('default', {})
                    viewer_type = uuid  # try the value of 'uuid' as a viewer name
                    linked_base = center_base
                    uuid = None
                    log.debug("using default metadata for %s: %s" % (viewer_type, e))

                try:
                    viewer_cls = self.task.find_viewer_by_name(viewer_type)
                except ValueError:
                    log.error("unknown viewer %s, uuid=%s" % (viewer_type, uuid))
                    continue
                log.debug("creating viewer %s with linked base %s" % (viewer_type, str(linked_base)))
                viewer = viewer_cls.create(self.control, linked_base, None, uuid)
                viewer.from_metadata_dict(e)

                # if there is a perspective, this pane_info will get replaced
                if first:
                    viewer.pane_info.CenterPane().DestroyOnClose()
                    self.set_focused_viewer(viewer)  # Initial focus is center pane
                    first = False
                else:
                    layer += 1
                    viewer.pane_info.Right().Layer(layer)
                self.viewers.append(viewer)
                self.mgr.AddPane(viewer.control, viewer.pane_info)
            if first:
                # just load default hex editor if nothing has been created
                viewers = ['hex']
                first = False

        if perspective:
            # The following creates a new pane_info based on the layout...
            self.mgr.LoadPerspective(perspective)

            # ...so we have to move this newly created pane_info back onto the
            # viewer
            for v in self.viewers:
                v.pane_info = self.mgr.GetPane(v.uuid)
        self.update_pane_names()
        self.mgr.Update()

    #### wx event handlers

    def force_focus(self, viewer):
        self.mgr.ActivatePane(viewer.control)
        self.update_pane_names()
        viewer.update_toolbar()

    def set_focused_viewer(self, viewer):
        self.focused_viewer = viewer
        self.focused_viewer_changed_event = viewer
        self.cursor_handler = viewer.linked_base
        viewer.linked_base.calc_action_enabled_flags()

    def on_pane_active(self, evt):
        # NOTE: evt.pane in this case is not an AuiPaneInfo object, it's the
        # AuiPaneInfo.window object
        if evt.pane is None:
            log.debug("skipping on_pane_active with no AuiPaneInfo object")
            return
        v = evt.pane.segment_viewer
        if v == self.focused_viewer:
            log.debug("on_pane_active: already current viewer %s" % v)
        else:
            log.debug("on_pane_active: activated viewer %s %s" % (v, v.window_title))
            self.set_focused_viewer(evt.pane.segment_viewer)

    def on_pane_close(self, evt):
        v = evt.pane.window.segment_viewer
        log.debug("on_pane_close: closed viewer %s %s" % (v, v.window_title))
        self.viewers.remove(v)
