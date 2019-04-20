import sys
import time

import wx
import wx.lib.scrolledpanel

from ..editor import get_editors

import logging
log = logging.getLogger(__name__)


class PreferencesDialog(wx.Dialog):
    border = 3

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Preferences", size=(700, 400), pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self.book = wx.Treebook(self, -1, style=wx.LB_LEFT)
        sizer.Add(self.book, 1, wx.ALL|wx.EXPAND, self.border)

        self.add_pages()

        # self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGED, self.OnPageChanged)
        # self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGING, self.OnPageChanging)

        btnsizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.SetDefault()
        btnsizer.AddButton(self.ok_btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.ALL|wx.EXPAND, self.border)

        self.Bind(wx.EVT_BUTTON, self.on_button)

        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)

    def add_pages(self):
        editors = get_editors()
        for e in editors:
            print(e, e.get_preferences())
            panel = PreferencesPanel(self.book, e, size=(500,500))
            # text = wx.StaticText(panel, -1, f"{e.editor_id}: {e.preferences_module} {e.preferences}")
            # sizer = wx.BoxSizer(wx.VERTICAL)
            # panel.SetSizer(sizer)
            # sizer.Add(text, 0, wx.ALL|wx.EXPAND, self.border)
            self.book.AddPage(panel, e.ui_name)

    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.persist_preferences()
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def persist_preferences(self):
        print("STUFF!")


class InfoField:
    same_line = True
    display_label = True

    # wx.Sizer proportion of the main control (not the label).  See the
    # wx.Sizer docs, but basically 0 will fix vertical size to initial size, >
    # 0 will fill available space based on the total proportion in the sizer.
    vertical_proportion = 0

    default_width = 100

    popup_width = 300

    def __init__(self, panel, settings, desc, prefs, attrib_name):
        self.panel = panel
        self.field_name = desc
        self.prefs = prefs
        self.attrib_name = attrib_name
        self.create(settings)
        self.add_to_parent()

    def is_displayed(self, layer):
        return True

    def show(self, state=True):
        self.container.Show(state)

    def hide(self):
        self.show(False)

    def create(self, settings):
        self.container = wx.Window(self.panel)
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.container.SetSizer(self.box)
        if self.display_label:
            self.label = wx.StaticText(self.container, label=self.field_name, style=wx.ST_ELLIPSIZE_END)
            bold_font = self.container.GetFont()
            bold_font.SetWeight(weight=wx.FONTWEIGHT_BOLD)
            self.label.SetFont(bold_font)
        self.create_all_controls(settings)
        if self.same_line and self.display_label:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            hbox.Add(self.label, 99, wx.ALIGN_CENTER)
            hbox.AddStretchSpacer(1)
            hbox.Add(self.ctrl, 0, wx.ALIGN_CENTER)
            for extra in self.extra_ctrls:
                hbox.Add(extra, 0, wx.ALIGN_CENTER)
            self.box.Add(hbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
        else:
            if self.display_label:
                self.box.Add(self.label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
                self.box.AddSpacer(self.panel.LABEL_SPACING)
            self.box.Add(self.ctrl, self.vertical_proportion, wx.EXPAND | wx.LEFT | wx.RIGHT, self.panel.SIDE_SPACING)
            for extra in self.extra_ctrls:
                self.box.Add(extra, 0, wx.ALIGN_CENTER)
        self.box.AddSpacer(self.panel.VALUE_SPACING)

    def create_all_controls(self, settings):
        self.ctrl = self.create_control(settings)
        self.extra_ctrls = self.create_extra_controls(settings)
        self.create_extra_event_handlers()

    def is_editable_control(self, ctrl):
        return ctrl == self.ctrl

    def create_extra_controls(self, settings):
        return []

    def create_extra_event_handlers(self):
        pass

    def add_to_parent(self):
        self.panel.sizer.Add(self.container, self.vertical_proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.ALIGN_TOP, 0)
        self.show(True)

    def fill_data(self):
        raise NotImplementedError

    def is_valid(self):
        return True

    def wants_focus(self):
        return False

    def set_focus(self):
        pass

    def process_command(self, cmd):
        # Override the normal refreshing of the InfoPanel when editing the
        # properties here because refreshing them messes up the text editing.
        self.panel.project.process_command(cmd, override_editable_properties_changed=False)


class LabelField(InfoField):
    alignment_style = wx.ALIGN_RIGHT

    def create_control(self, settings):
        c = wx.StaticText(self.container, style=self.alignment_style)
        return c


class TextEditField(InfoField):
    def create_control(self, settings):
        c = wx.TextCtrl(self.container)
        c.Bind(wx.EVT_TEXT, self.on_text_changed)
        c.SetEditable(True)
        return c

    def fill_data(self):
        try:
            text = self.get_value()
            self.ctrl.Enable(True)
        except IndexError:
            text = ""
            self.ctrl.Enable(False)
        self.ctrl.ChangeValue(text)
        self.is_valid()

    def get_value(self):
        """Return a text representation of the attribute so populate the
        TextCtrl."""
        raise NotImplementedError

    def is_valid(self):
        c = self.ctrl
        c.SetBackgroundColour("#FFFFFF")
        try:
            self.parse_from_ctrl()
            valid = True
        except Exception:
            c.SetBackgroundColour("#FF8080")
            valid = False
        self.ctrl.Refresh()
        return valid

    def parse_from_ctrl(self):
        return self.ctrl.GetValue()

    def on_text_changed(self, evt):
        if self.is_valid():
            value = self.parse_from_ctrl()
            setattr(self.prefs, self.attrib_name, value)

    def initial_text_input(self, text):
        self.ctrl.SetValue(text)
        self.ctrl.SetInsertionPointEnd()  # (self.ctrl.GetLastPosition())


class IntField(TextEditField):
    def get_value(self):
        value = getattr(self.prefs, self.attrib_name)
        text = str(value)
        return text

    def parse_from_ctrl(self):
        return int(self.ctrl.GetValue())


class BoolField(InfoField):
    def create_control(self, settings):
        c = wx.CheckBox(self.container)
        c.Bind(wx.EVT_CHECKBOX, self.on_toggle_changed)
        return c

    def fill_data(self):
        state = self.get_value()
        self.ctrl.SetValue(state)
        self.is_valid()

    def get_value(self):
        """Return a control representation of the attribute so populate the
        TextCtrl."""
        state = getattr(self.prefs, self.attrib_name)
        return state

    def is_valid(self):
        return True

    def parse_from_ctrl(self):
        return self.ctrl.GetValue()

    def on_toggle_changed(self, evt):
        if self.is_valid():
            value = self.parse_from_ctrl()
            setattr(self.prefs, self.attrib_name, value)


class ChoiceField(InfoField):
    def get_value(self, layer):
        return ""

    def fill_data(self):
        default_choice = self.get_value()
        self.ctrl.SetSelection(self.choices.index(default_choice))

    def get_value(self):
        state = getattr(self.prefs, self.attrib_name)
        return state

    def create_control(self, settings):
        self.choices = settings
        c = wx.Choice(self.container, choices=[str(c) for c in self.choices])
        c.Bind(wx.EVT_CHOICE, self.drop_down_changed)
        return c

    def drop_down_changed(self, event):
        index = self.ctrl.GetSelection()
        setattr(self.prefs, self.attrib_name, self.choices[index])


known_fields = {
    "int": IntField,
    "bool": BoolField,
    # "Font": FontField,
}


def find_field(field_type):
    if ":" in field_type:
        field_cls, field_settings = field_type.split(":", 1)
    try:
        field_cls = known_fields[field_type]
        settings = None
    except TypeError:
        field_cls = ChoiceField
        settings = field_type[:]
    except KeyError:
        log.error(f"Unknown preference type {field_type}")
        raise
    return field_cls, settings

def calc_field(parent, prefs, attrib_name, field_type, desc):
    field_cls, settings = find_field(field_type)
    field = field_cls(parent, settings, desc, prefs, attrib_name)
    field.fill_data()
    return field


PANELTYPE = wx.lib.scrolledpanel.ScrolledPanel
class PreferencesPanel(PANELTYPE):
    """
    A panel for displaying and manipulating the properties of a layer.
    """
    LABEL_SPACING = 0
    VALUE_SPACING = 3
    SIDE_SPACING = 5

    window_name = "InfoPanel"

    def __init__(self, parent, editor, size=(-1,-1)):
        PANELTYPE.__init__(self, parent, name=self.window_name, size=size)

        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.display_panel_for_editor(editor)

    def display_panel_for_editor(self, editor):
        self.editor = editor
        prefs = editor.preferences

        self.sizer.AddSpacer(self.LABEL_SPACING)

        self.fields = []
        for field_info in prefs.display_order:
            attrib_cls = None
            desc = None
            if isinstance(field_info, str):
                attrib_name = field_info
            else:
                try:
                    attrib_name, attrib_cls_name, desc = field_info
                except ValueError:
                    try:
                        attrib_name, attrib_cls_name = field_info
                    except ValueError:
                        attrib_name = field_info[0]
            desc = attrib_name.replace("_", " ").title()
            if attrib_cls_name is None:
                attrib = getattr(prefs, attrib_name)
                attrib_cls_name = attrib.__class__.__name__

            try:
                field = calc_field(self, prefs, attrib_name, attrib_cls_name, desc)
                self.fields.append(field)
            except KeyError:
                pass

        self.sizer.Layout()
