import sys

import numpy as np

import wx
import wx.adv
import wx.lib.buttons as buttons
import wx.lib.scrolledpanel
from wx.lib.expando import ExpandoTextCtrl
from wx.lib.stattext import GenStaticText  # standard static text can't set background color on some platforms

from atrip.char_mapping import internal_to_atascii, atascii_to_internal
from ..arch.ui.antic_colors import AnticColorDialog
from sawx.utils.runtime import get_all_subclasses

import logging
from functools import reduce
log = logging.getLogger(__name__)

def reduce_from_little_endian(raw):
    try:
        value = reduce(lambda x, y: x + (y << 8), raw)  #  convert to little endian
    except TypeError:
        # no array values, probably an attempt to display before the
        # segment is loaded.
        value = 0
    return value

class InfoField(object):
    keyword = ""
    same_line = False
    display_label = True
    use_edit_timer = False

    # wx.Sizer proportion of the main control (not the label).  See the
    # wx.Sizer docs, but basically 0 will fix vertical size to initial size, >
    # 0 will fill available space based on the total proportion in the sizer.
    vertical_proportion = 0

    default_width = 100

    popup_width = 300

    extra_vertical_spacing = 0

    edit_timer_delay = 300  # ms

    def __init__(self, panel, info):
        self.panel = panel
        self.set_args(info)
        self.create()

    @property
    def undo_label(self):
        return "Change %s" % self.field_name

    def set_args(self, args):
        self.field_name = args[0]
        self.byte_offset = args[1]
        self.byte_count = args[2]
        if len(args) > 3:
            val = args[3]
            try:
                self.max_val = int(val)
            except ValueError:
                self.attr_name_max_val = val

    def is_displayed(self, linked_base):
        return True

    def show(self, state=True):
        self.parent.Show(state)

    def hide(self):
        self.show(False)

    def enable(self, state=True):
        self.parent.Enable(state)
        self.ctrl.Enable(state)

    def create(self):
        self.parent = wx.Window(self.panel)
        self.box =  wx.BoxSizer(wx.VERTICAL)
        self.parent.SetSizer(self.box)
        if self.display_label:
            self.label = wx.StaticText(self.parent, label=self.field_name, style=wx.ST_ELLIPSIZE_END)
            bold_font = self.parent.GetFont()
            bold_font.SetWeight(weight=wx.FONTWEIGHT_BOLD)
            self.label.SetFont(bold_font)
        self.create_all_controls()
        if self.same_line and self.display_label:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            hbox.Add(self.label, 99, wx.ALIGN_CENTER)
            hbox.AddStretchSpacer(1)
            hbox.Add(self.ctrl, 0, wx.ALIGN_CENTER)
            for extra in self.extra_ctrls:
                hbox.Add(extra, 0, wx.ALIGN_CENTER)
            if self.extra_vertical_spacing > 0:
                self.box.AddSpacer(self.extra_vertical_spacing)
            self.box.Add(hbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
            if self.extra_vertical_spacing > 0:
                self.box.AddSpacer(self.extra_vertical_spacing)
        else:
            if self.display_label:
                self.box.Add(self.label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
                self.box.AddSpacer(self.panel.LABEL_SPACING)
            self.box.Add(self.ctrl, self.vertical_proportion, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
            for extra in self.extra_ctrls:
                hbox.Add(extra, 0, wx.ALIGN_CENTER)
        self.box.AddSpacer(self.panel.VALUE_SPACING)

    def create_all_controls(self):
        if self.use_edit_timer:
            self.create_edit_timer()
        self.ctrl = self.create_control()
        if sys.platform.startswith("win"):
            self.ctrl.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel_scroll)
        self.extra_ctrls = self.create_extra_controls()
        self.set_control_limits()

    def create_edit_timer(self):
        self.edit_timer = wx.Timer(self.panel)
        self.panel.Bind(wx.EVT_TIMER, self.on_edit_timer_elapsed, self.edit_timer)

    def start_edit_timer(self, evt=None):
        self.edit_timer.Start(self.edit_timer_delay, oneShot=True)

    def on_edit_timer_elapsed(self, evt):
        self.edit_timer_callback()
        evt.Skip()

    def edit_timer_callback(self):
        raise RuntimeError("no edit timer callback set")

    def is_editable_control(self, ctrl):
        return ctrl == self.ctrl

    def set_control_limits(self):
        pass

    def create_extra_controls(self):
        return []

    def add_to_parent(self):
        self.panel.sizer.Add(self.parent, self.vertical_proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.ALIGN_TOP, 0)
        self.show(True)

    def fill_data(self, linked_base):
        raise NotImplementedError

    def clear_data(self):
        raise NotImplementedError

    def has_focus(self):
        return self.ctrl.FindFocus() == self.ctrl

    def get_focus_params(self):
        pass

    def set_focus_params(self, params):
        pass

    def get_source_bytes(self, linked_base):
        raw = linked_base.segment[self.byte_offset:self.byte_offset+self.byte_count].copy()
        return raw

    def is_valid(self):
        return True

    def wants_focus(self):
        return False

    def set_focus(self):
        pass

    def on_mouse_wheel_scroll(self, event):
        screen_point = event.GetPosition()
        size = self.ctrl.GetSize()
        if screen_point.x < 0 or screen_point.y < 0 or screen_point.x > size.x or screen_point.y > size.y:
#            print "Mouse not over info panel %s: trying map!" % self
            self.panel.linked_base.control.on_mouse_wheel_scroll(event)
            return

        event.Skip()


class LabelField(InfoField):
    keyword = "label"
    same_line = True
    extra_vertical_spacing = 3

    def set_args(self, args):
        self.field_name = args[0]
        self.attr_name = args[1]
        self.max_val = args[2]

    def create_control(self):
        c = GenStaticText(self.parent, style=wx.ALIGN_RIGHT)
        return c

    def fill_data(self, linked_base):
        try:
            value = getattr(self.panel.linked_base.segment.jumpman_playfield_model, self.attr_name)
        except AttributeError:
            value = 0
        self.ctrl.SetLabel(str(value))
        self.set_background(linked_base, value <= self.max_val)

    def set_background(self, linked_base, valid):
        if valid:
            color = linked_base.cached_preferences.empty_background_color
        else:
            color = linked_base.cached_preferences.error_background_color
        self.ctrl.SetBackgroundColour(color)

    def clear_data(self):
        self.ctrl.SetLabel("")
        self.set_background(self.panel.linked_base, True)


class MultiLineLabelField(InfoField):
    keyword = "multi_line_label"
    same_line = False
    extra_vertical_spacing = 3

    def set_args(self, args):
        self.field_name = args[0]
        self.attr_name = args[1]

    def create_control(self):
        c = GenStaticText(self.parent, style=wx.ALIGN_LEFT)
        return c

    def fill_data(self, linked_base):
        try:
            value = getattr(self.panel.linked_base.segment.jumpman_playfield_model, self.attr_name)
        except AttributeError:
            value = ""
        self.ctrl.SetLabel(str(value).rstrip() + "\n")

    def clear_data(self):
        self.ctrl.SetLabel("")


class TextEditField(InfoField):
    keyword = "text"
    same_line = True
    wide = False
    use_edit_timer = True

    def create_control(self):
        if self.wide:
            size = (200, -1)
        else:
            size = (-1, -1)
        c = wx.TextCtrl(self.parent, size=size)
        c.Bind(wx.EVT_TEXT, self.start_edit_timer)
        c.SetEditable(True)
        return c

    def edit_timer_callback(self):
        linked_base = self.panel.linked_base
        self.process_text_change(linked_base)

    def set_control_limits(self):
        if self.byte_count > 0:
            self.ctrl.SetMaxLength(self.byte_count)

    def fill_data(self, linked_base):
        try:
            raw = self.get_source_bytes(linked_base)
            text = self.bytes_to_control_data(raw)
            self.ctrl.Enable(True)
        except IndexError:
            text = ""
            self.ctrl.Enable(False)
        except TypeError:
            text = ""
            self.ctrl.Enable(False)
        self.ctrl.ChangeValue(text)
        self.is_valid()

    def clear_data(self):
        self.ctrl.ChangeValue("")

    def get_focus_params(self):
        return self.ctrl.GetInsertionPoint()

    def set_focus_params(self, caret):
        self.ctrl.SetInsertionPoint(caret)

    def is_valid(self):
        c = self.ctrl
        c.SetBackgroundColour("#FFFFFF")
        try:
            self.parse_from_control()
            valid = True
        except Exception as e:
            log.debug("TextEditField: %s" % e)
            c.SetBackgroundColour("#FF8080")
            valid = False
        self.ctrl.Refresh()
        return valid

    def parse_from_control(self):
        return self.ctrl.GetValue()

    def initial_text_input(self, text):
        self.ctrl.ChangeValue(text)
        self.ctrl.SetInsertionPointEnd()#(self.ctrl.GetLastPosition())

    def bytes_to_control_data(self, raw):
        raw = self.map_bytes_to_text(raw)
        text = raw.tobytes().lstrip()
        if self.has_focus():
            data = self.parse_from_control()
            text = text[0:len(data)]
        else:
            text = text.rstrip()
        return text

    def map_bytes_to_text(self, raw):
        raw[raw < 32] = 32
        r = raw > 95
        raw[r] = raw[r] - 32  # convert lower case to upper
        raw[raw > 96] = 32
        return raw

    def parsed_to_bytes(self, parsed_data):
        raw = np.zeros([self.byte_count],dtype=np.uint8)
        text = np.fromstring(parsed_data, dtype=np.uint8)
        text = text[0:self.byte_count]
        text = self.map_parsed_to_bytes(text)
        raw[0:len(text)] = text
        return raw

    def map_parsed_to_bytes(self, text):
        return text

    def process_text_change(self, linked_base):
        if self.is_valid():
            data = self.parse_from_control()
            raw = self.parsed_to_bytes(data)
            linked_base.change_bytes(self.byte_offset, self.byte_offset + self.byte_count, raw, self.undo_label)


class AtasciiC0(TextEditField):
    keyword = "atascii_gr2_0xc0"
    high_bits = 0xc0
    wide = True

    def parsed_to_bytes(self, parsed_data):
        raw = np.zeros([self.byte_count],dtype=np.uint8) | self.high_bits
        text = np.fromstring(parsed_data, dtype=np.uint8)
        text = text[0:self.byte_count]
        text = self.map_parsed_to_bytes(text)
        # Center text
        i = (self.byte_count - len(text)) // 2
        raw[i:i + len(text)] = text
        return raw

    def map_bytes_to_text(self, raw):
        raw = raw & 0x3f
        return internal_to_atascii[raw]

    def map_parsed_to_bytes(self, text):
        text = atascii_to_internal[text]
        return text | self.high_bits


class UIntEditField(TextEditField):
    keyword = "uint"
    same_line = True

    def set_control_limits(self):
        pass

    def bytes_to_control_data(self, raw):
        value = reduce_from_little_endian(raw)
        text = str(value)
        return text

    def parse_from_control(self):
        value = int(self.ctrl.GetValue())
        if hasattr(self, "attr_name_max_val") and hasattr(self.panel.linked_base, self.attr_name_max_val):
            maxval = getattr(self.panel.linked_base.segment.jumpman_playfield_model, self.attr_name_max_val)
            if value > maxval:
                raise ValueError("%d out of range for attribute %s max of %d" % (value, self.attr_name_max_val, maxval))
        if hasattr(self, "max_val"):
            if value > self.max_val:
                raise ValueError("%d greater than %d" % (value, self.maxval))
        if self.byte_count == 1 and value >=0 and value < 256:
            return value
        elif self.byte_count == 2 and value >=0 and value < 256 * 256:
            return value
        raise ValueError("%d out of range for %d bytes" % (value, self.byte_count))

    def parsed_to_bytes(self, parsed_data):
        raw = np.empty([self.byte_count], dtype=np.uint8)
        if self.byte_count == 1:
            raw[0] = parsed_data
        elif self.byte_count == 2:
            v = raw.view(dtype='<u2')
            v[0] = parsed_data
        return raw


class AnticColorsField(InfoField):
    keyword = "antic_colors"
    same_line = True
    register_names = ["%x %s" % (i + 0x282a, n) for i, n in enumerate([
    "(unused)",
    "Jumpman Shadow",
    "Player 2",
    "Player 3",
    "Girder & up ropes",
    "Ladder & down ropes",
    "Coins",
    "Bullets",
    "Background",
    ])]

    def create_control(self):
        c = wx.Button(self.parent, -1, "Set Colors")
        c.Bind(wx.EVT_BUTTON, self.on_colors)
        return c

    def fill_data(self, linked_base):
        pass

    def clear_data(self):
        pass

    def on_colors(self, evt):
        linked_base = self.panel.linked_base
        raw = self.get_source_bytes(linked_base)
        dlg = AnticColorDialog(self.ctrl, raw, linked_base.cached_preferences, self.register_names)
        if dlg.ShowModal() == wx.ID_OK:
            linked_base.change_bytes(self.byte_offset, self.byte_offset + self.byte_count, dlg.colors, self.undo_label)
            # # linked_base.force_data_model_update()
            linked_base.document.byte_style_changed_event(flags=True)


class DropDownField(InfoField):
    keyword = "dropdown"
    same_line = True

    def set_args(self, args):
        self.field_name = args[0]
        self.byte_offset = args[1]
        self.byte_count = args[2]
        self.choices = args[3]

    def get_choices(self, linked_base):
        return self.choices

    def bytes_to_control_data(self, raw):
        value = reduce_from_little_endian(raw)
        value = min(value, len(self.choices) - 1)
        return value

    def fill_data(self, linked_base):
        choices = self.get_choices(linked_base)
        self.ctrl.SetItems(choices)
        raw = self.get_source_bytes(linked_base)
        default_choice = self.bytes_to_control_data(raw)
        self.ctrl.SetSelection(default_choice)

    def clear_data(self):
        pass

    def create_control(self):
        c = wx.Choice(self.parent, choices=[])
        c.Bind(wx.EVT_CHOICE, self.drop_down_changed)
        return c

    def drop_down_changed(self, event):
        raw = np.zeros([self.byte_count],dtype=np.uint8)
        raw[0] = self.ctrl.GetSelection()
        self.panel.linked_base.change_bytes(self.byte_offset, self.byte_offset + self.byte_count, raw, self.undo_label)


class CoinsNeededField(DropDownField):
    keyword = "coins_needed"
    same_line = True

    def bytes_to_control_data(self, raw):
        try:
            e = self.panel.linked_base.segment.jumpman_playfield_model
        except AttributeError:
            return 0
        num = e.num_coins
        value = reduce_from_little_endian(raw)
        diff = num - value
        if diff < 0:
            diff = 0
        diff = min(diff, len(self.choices) - 1)

        if e.coin_harvest_diff < 0:
            # First time! Calculate the offset to use subsequently
            e.coin_harvest_diff = diff
        return diff

    def drop_down_changed(self, event):
        e = self.panel.linked_base.segment.jumpman_playfield_model
        e.coin_harvest_diff = self.ctrl.GetSelection()
        raw = np.zeros([self.byte_count],dtype=np.uint8)
        raw[0] = max(0, e.num_coins - e.coin_harvest_diff)
        self.panel.linked_base.change_bytes(self.byte_offset, self.byte_offset + self.byte_count, raw, self.undo_label)


PANELTYPE = wx.lib.scrolledpanel.ScrolledPanel


class InfoPanel(PANELTYPE):

    """
    A panel for displaying and manipulating the properties of a linked_base.
    """
    LABEL_SPACING = 0
    VALUE_SPACING = 3
    SIDE_SPACING = 5

    def __init__(self, parent, linked_base, fields=None, **kwargs):
        self.linked_base = linked_base

        if fields is not None:
            self.fields = fields
        self.focus_on_input = None
        self.last_change_count = -1

        PANELTYPE.__init__(self, parent)

        # Mac/Win needs this, otherwise background color is black
        self.SetBackgroundColour(linked_base.cached_preferences.empty_background_color)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.init_fields(self.fields)

    def recalc_view(self):
        self.set_fields()

    def refresh_view(self):
        if self.IsShown():
            log.debug("refreshing %s" % self)
            self.recalc_view()
        else:
            log.debug("skipping refresh of hidden %s" % self)

    def init_fields(self, fields):
        self.sizer.AddSpacer(self.LABEL_SPACING)

        self.Freeze()

        focus = None
        self.current_fields = []
        for info in fields:
            field = self.create_field(info)
            if field is None:
                log.debug("init_fields: Skipping %s" % str(info))
                continue
            field.add_to_parent()
            field.fill_data(self.linked_base)
            if field.wants_focus():
                focus = field
            self.current_fields.append(field)

        self.constrain_size(focus)

        self.Thaw()
        self.Update()
        self.Refresh()

    def create_field(self, field_info):
        keyword = field_info[0]
        field = None
        subclasses = get_all_subclasses(InfoField)
        for kls in get_all_subclasses(InfoField):
            if keyword == kls.keyword:
                field = kls(self, field_info[1:])
                break
        return field

    def is_valid_data(self):
        """Override this in subclasses to disable entire panel if there is 
        no valid data to show.
        """
        return True

    def set_fields(self):
        enabled = self.is_valid_data()
        focus = None
        for field in self.current_fields:
            if field.has_focus():
                params = field.get_focus_params()
            else:
                params = None
            if enabled:
                field.fill_data(self.linked_base)
                if params is not None:
                    field.set_focus_params(params)
                    focus = field
            else:
                field.clear_data()
            field.enable(enabled)
        self.constrain_size(focus)

    def constrain_size(self, focus=None):
        self.sizer.Layout()
        self.focus_on_input = focus
        if focus is not None:
            self.ScrollChildIntoView(focus.ctrl)
        self.SetupScrolling(scroll_x=False, scrollToTop=False, scrollIntoView=True)

    def process_initial_key(self, event, text):
        """ Uses keyboard input from another control to set the focus to the
        previously noted info field and process the text there.
        """
        if self.focus_on_input is not None:
            self.focus_on_input.set_focus()
            self.ScrollChildIntoView(self.focus_on_input.ctrl)
            self.focus_on_input.initial_text_input(text)
            return True
        return False
