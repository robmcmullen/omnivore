# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

from omnivore_framework.editor import OmnivoreEditor
from omnivore_framework.utils.wx.tilemanager import TileManager
from omnivore_framework.templates import get_template

import logging
log = logging.getLogger(__name__)


class DummyLinkedBase(object):
    segment = None
    segment_number = 0

class DummyFocusedViewer(object):
    linked_base = DummyLinkedBase


class TileManagerBase(OmnivoreEditor):
    """Base class for editors that use the tile manager as the central window
    manager
    """
    name = "omnivore.tile_manager_base"
    pretty_name = "Tile Manager Base"

    default_viewers = "dummy"

    def __init__(self, action_factory_lookup=None):
        OmnivoreEditor.__init__(self, action_factory_lookup)
        self.focused_viewer = None
        self.viewers = []

    def prepare_destroy(self):
        self.focused_viewer = None
        # Operate on copy of list because you can't iterate and remove from the
        # same list
        for v in list(self.viewers):
            log.debug(f"Closing viewer: {v}")
            self.viewers.remove(v)
            v.prepare_for_destroy()
            del v

    def create_control(self, parent):
        """Creates the `TileManager` control that will manage all the viewers
        """

        panel = TileManager(parent, toggle_checker=self.check_viewer_center_base)
        panel.Bind(TileManager.EVT_CLIENT_ACTIVATED, self.on_viewer_active)
        panel.Bind(TileManager.EVT_CLIENT_CLOSE, self.on_viewer_close)
        panel.Bind(TileManager.EVT_CLIENT_REPLACE, self.on_viewer_replace)
        panel.Bind(TileManager.EVT_CLIENT_TOGGLE_REQUESTED, self.on_viewer_link)
        return panel

    def get_default_layout(self):
        template_name = self.document.calc_layout_template_name(self.name)
        log.debug("template from: %s" % template_name)
        try:
            data = get_template(template_name)
        except OSError as err:
            log.error(f"Failed loading template: {err}")
            layout = {}
        else:
            try:
                layout = json.loads(data)
            except ValueError:
                log.error("invalid data in default layout")
                layout = {}
        return layout

    def get_layout_metadata(self, keyword):
        """get the TileManager layout
        """
        layout_dict = self.editor_metadata.get(keyword, {})
        if not layout_dict:
            layout_dict = self.get_default_layout().get(keyword, {})
        return layout_dict

    def restore_layout_and_viewers(self):
        viewers = self.get_layout_metadata("viewers")
        if viewers:
            layout = self.get_layout_metadata("layout")
            if layout:
                self.control.restore_layout(layout)
        else:
            viewers = self.default_viewers
        log.critical(viewers)






    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        viewers = e.get('viewers', [])
        log.debug("metadata: viewers=%s" % str(viewers))
        
        if not viewers:
            try:
                e_default = self.get_default_layout()
                print(("using defaults from template: template=%s" % str(e_default)))
            except OSError:
                log.error("No template for default layout; falling back to minimal setup.")
            else:
                e.update(e_default)
                viewers = e.get('viewers', [])
            log.debug("from layout: viewers=%s" % str(viewers))

        layout = e.get('layout', {})
        log.debug("metadata: layout=%s" % str(layout))

        viewer_metadata = {}
        for v in viewers:
            viewer_metadata[v['uuid']] = v
            log.debug("metadata: viewer[%s]=%s" % (v['uuid'], str(v)))

        log.debug("task arguments: '%s'" % self.task_arguments)
        if self.task_arguments or not viewer_metadata:
            names = self.task_arguments if self.task_arguments else self.default_viewers
            log.debug("overriding viewers: %s" % str(names))
            override_viewer_metadata = {}
            for viewer_name in names.split(","):
                if viewer_name == "emulator":
                    continue
                override_viewer_metadata[viewer_name.strip()] = {}
                log.debug("metadata: clearing viewer[%s] because specified in task args" % (viewer_name.strip()))
            if override_viewer_metadata:
                # found some specified viewers, so override the default layout
                viewer_metadata = override_viewer_metadata
                layout = {}  # empty layout so it isn't cluttered with unused windows

        linked_bases = {}
        for b in e.get('linked bases', []):
            base = LinkedBase(editor=self)
            base.from_metadata_dict(b)
            linked_bases[base.uuid] = base
            log.debug("metadata: linked_base[%s]=%s" % (base.uuid, base))
        uuid = e.get("center_base", None)
        try:
            self.center_base = linked_bases[uuid]
        except KeyError:
            self.center_base = LinkedBase(editor=self)
        self.create_viewers(layout, viewer_metadata, e, linked_bases)
        viewer = None
        if 'focused viewer' in e:
            u = e['focused viewer']
            viewer = self.find_viewer_by_uuid(u)
        if viewer is None:
            for viewer in self.viewers:
                if not self.control.in_sidebar(viewer.control):
                    break
        print(("setting focus to %s" % viewer))
        self.set_focused_viewer(viewer)
        self.task.segments_changed = self.document.segments

    def to_metadata_dict(self, mdict, document):
        self.prepare_metadata_for_save()
        mdict["layout"] = self.control.calc_layout()
        mdict["viewers"] = []
        bases = {}
        for v in self.viewers:
            b = v.linked_base
            bases[b.uuid] = b
            e = {"linked base": v.linked_base.uuid}
            v.to_metadata_dict(e, document)
            mdict["viewers"].append(e)
        if self.center_base is not None:
            bases[self.center_base.uuid] = self.center_base
            mdict["center_base"] = self.center_base.uuid
        else:
            mdict["center_base"] = None
        mdict["linked bases"] = []
        for u, b in bases.items():
            e = {}
            b.to_metadata_dict(e, document)
            mdict["linked bases"].append(e)
        mdict["focused viewer"] = self.focused_viewer.uuid
        # if document == self.document:
        #     # If we're saving the document currently displayed, save the
        #     # display parameters too.
        #     mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper

    def prepare_metadata_for_save(self):
        pass

    #### viewer utilities

    def reconfigure_viewers(self):
        self.update_viewer_names()

    def update_viewer_names(self):
        for viewer in self.viewers:
            viewer.update_caption()
        self.control.update_captions()

    def add_viewer(self, viewer_or_viewer_cls, linked_base=None, replace_uuid=None):
        if hasattr(viewer_or_viewer_cls, "control"):
            viewer = viewer_or_viewer_cls
        else:
            if linked_base is None:
                if self.focused_viewer is not None:
                    linked_base = self.focused_viewer.linked_base
                else:
                    raise RuntimeError("Creating a viewer with no linked base and no focused viewer")
            viewer = viewer_or_viewer_cls.viewer_factory(self.control, linked_base)
        print("VIWER", viewer, type(viewer_or_viewer_cls), linked_base)
        print("SEGMENT", linked_base.segment)
        if replace_uuid:
            viewer.uuid = replace_uuid
        self.viewers.append(viewer)
        self.control.add(viewer.control, viewer.uuid)
        viewer.recalc_data_model()
        self.update_pane_names()
        return viewer

    def replace_viewer(self, viewer_to_replace, new_viewer, linked_base):
        # self.viewers.remove(viewer_to_replace)
        # viewer_to_replace.prepare_for_destroy()
        created_viewer = self.add_viewer(new_viewer, linked_base, replace_uuid=viewer_to_replace.uuid)
        # self.set_focused_viewer(created_viewer)
        # del viewer_to_replace

    def replace_focused_viewer(self, linked_base):
        viewer_cls = self.focused_viewer.__class__
        self.replace_viewer(self.focused_viewer, viewer_cls, linked_base)

    def verify_center_base_is_used(self):
        if self.center_base is not None:
            for v in self.viewers:
                if v.linked_base == self.center_base:
                    break
            else:
                self.center_base = None
        print(f"Center base is: {self.center_base}")

    def unlink_viewer(self):
        number = self.focused_viewer.linked_base.segment_number
        base = LinkedBase(editor=self)
        base.view_segment_number(number)
        self.replace_focused_viewer(base)
        self.verify_center_base_is_used()

    def link_viewer(self):
        if self.center_base is None:
            self.center_base = self.focused_viewer.linked_base
        else:
            base = self.center_base
            self.replace_focused_viewer(base)

    def check_viewer_center_base(self, viewer_control, toggle_id):
        try:
            v = viewer_control.segment_viewer
        except AttributeError:
            state = True
        else:
            state = v.linked_base == self.center_base
        return state

    def create_viewers(self, viewer_metadata, default_viewer_metadata, linked_bases):
        # Create a set of viewers from a list
        import pprint
        log.debug("viewer_metadata: %s" % str(list(viewer_metadata.keys())))

        self.document.find_initial_visible_segment(self.center_base)

        layer = 0
        viewers = list(viewer_metadata.keys())

        center_base_used = False
        while not self.viewers:
            for uuid in viewers:
                log.debug("loading viewer: %s" % uuid)
                e = viewer_metadata[uuid]
                if e:
                    viewer_type = e['name']
                else:  # either not a uuid or an unknown uuid
                    viewer_type = uuid  # try the value of 'uuid' as a viewer name
                try:
                    viewer_cls = self.task.find_viewer_by_name(viewer_type)
                except ValueError:
                    log.error("unknown viewer %s, uuid=%s" % (viewer_type, uuid))
                    continue
                log.debug("identified viewer: %s" % viewer_cls)

                if e:
                    try:
                        linked_base = linked_bases[e['linked base']]
                    except KeyError:
                        linked_base = self.center_base
                    log.debug("recreating viewer %s: %s" % (viewer_type, uuid))
                else:  # either not a uuid or an unknown uuid
                    linked_base = viewer_cls.calc_segment_specific_linked_base(self)
                    if linked_base is None:
                        linked_base = self.center_base
                    log.debug("using default metadata for %s" % (viewer_type))
                if linked_base == self.center_base:
                    center_base_used = True

                log.debug("creating viewer %s (%s) with linked base %s" % (uuid, viewer_type, str(linked_base)))
                viewer = viewer_cls.viewer_factory(self.control, linked_base, None, uuid, e)
                log.debug("created viewer %s (%s)" % (viewer.uuid, viewer.name))

                self.viewers.append(viewer)
                if not self.control.replace_by_uuid(viewer.control, viewer.uuid):
                    log.debug("viewer %s not found, adding in new pane" % viewer.uuid)
                    self.control.add(viewer.control, viewer.uuid)

            if not self.viewers:
                # just load default hex editor if nothing has been created
                viewers = ['hex']
                first = False

        if not center_base_used:
            self.center_base = None
        self.update_pane_names()

    def find_viewer_by_uuid(self, u):
        for v in self.viewers:
            if u == v.uuid:
                return v
        return None

    #### wx event handlers

    def force_focus(self, viewer):
        self.control.force_focus(viewer.uuid)
        self.update_pane_names()
        viewer.update_toolbar()

    def set_focused_viewer(self, viewer):
        self.focused_viewer = viewer
        self.focused_viewer_changed_event = viewer
        self.caret_handler = viewer.linked_base
        viewer.linked_base.calc_action_enabled_flags()
        viewer.linked_base.segment_selected_event = viewer.linked_base.segment_number

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

            # Keep a reference to the linked base
            linked_base_save = v.linked_base

            self.viewers.remove(v)
            v.prepare_for_destroy()

            from .. import viewers as omnivore8bit_viewers
            if not self.viewers:
                v = self.add_viewer(omnivore8bit_viewers.PlaceholderViewer, linked_base_save)
            self.set_focused_viewer(self.viewers[0])
            del v

    def on_viewer_replace(self, evt):
        try:
            v = evt.child.segment_viewer
        except AttributeError:
            # must be an empty window (a multisash window that has no segment
            # viewer). It can be closed without any further action.
            pass
        else:
            log.debug("on_viewer_replace: closing viewer %s %s for replacement" % (v, v.window_title))

            # Keep a reference to the linked base
            linked_base_save = v.linked_base

            self.viewers.remove(v)
            v.prepare_for_destroy()
            self.set_focused_viewer(evt.replacement_child.segment_viewer)
            del v

    def on_viewer_link(self, evt):
        try:
            v = evt.child.segment_viewer
        except AttributeError:
            # must be an empty window (a multisash window that has no segment
            # viewer). It can be closed without any further action.
            pass
        else:
            toggle = evt.GetInt()
            desired_state = evt.IsChecked()
            log.debug("on_viewer_replace: linking viewer %s %s: %s" % (v, v.window_title, desired_state))
            if desired_state:
                print("LINKED!")
                self.link_viewer()
            else:
                print("UNLINKED!")
                self.unlink_viewer()
