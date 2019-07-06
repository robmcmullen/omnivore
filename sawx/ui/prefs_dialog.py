import sys
import time

import wx
import wx.lib.scrolledpanel
import wx.lib.filebrowsebutton as filebrowse

from . import buttons
from . import fonts
from .. import preferences
from ..editor import get_editors

import logging
log = logging.getLogger(__name__)


class PreferencesDialog(wx.Dialog):
    border = 3

    def __init__(self, parent, initial_page_name=None):
        wx.Dialog.__init__(self, parent, -1, "Preferences", size=(700, 400), pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self.book = wx.Treebook(self, -1, style=wx.LB_LEFT)
        sizer.Add(self.book, 1, wx.ALL|wx.EXPAND, self.border)

        self.add_pages()
        if initial_page_name:
            self.show_page(initial_page_name)

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
        panel = ApplicationPreferencesPanel(self.book)
        self.book.AddPage(panel, panel.prefs.ui_name)

        editors = get_editors()
        for editor in editors:
            try:
                panel = EditorPreferencesPanel(self.book, editor, size=(500,500))
            except RuntimeError as e:
                # this editor has no preferences or preferences are same as its
                # superclass
                log.debug(f"Failed creating preference panel for {editor.ui_name}: {e}")
                pass
            else:
                self.book.AddPage(panel, editor.ui_name)

    def show_page(self, name):
        for index in range(self.book.GetPageCount()):
            if name == self.book.GetPageText(index):
                self.book.ChangeSelection(index)
                break

    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.commit_preferences()
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def commit_preferences(self):
        for i in range(self.book.GetPageCount()):
            panel = self.book.GetPage(i)
            panel.accept_preferences()


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

    def get_value(self):
        return getattr(self.prefs, self.attrib_name)

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
        self.label.Bind(wx.EVT_LEFT_DOWN, self.on_label_clicked)
        return c

    def fill_data(self):
        state = self.get_value()
        self.ctrl.SetValue(state)
        self.is_valid()

    def is_valid(self):
        return True

    def parse_from_ctrl(self):
        return self.ctrl.GetValue()

    def on_toggle_changed(self, evt):
        if self.is_valid():
            value = self.parse_from_ctrl()
            setattr(self.prefs, self.attrib_name, value)

    def on_label_clicked(self, evt):
        self.ctrl.SetValue(not self.ctrl.GetValue())
        self.on_toggle_changed(evt)


class ChoiceField(InfoField):
    def fill_data(self):
        default_choice = self.get_value()
        self.ctrl.SetSelection(self.choices.index(default_choice))

    def create_control(self, settings):
        self.choices = settings
        c = wx.Choice(self.container, choices=[str(c) for c in self.choices])
        c.Bind(wx.EVT_CHOICE, self.drop_down_changed)
        return c

    def drop_down_changed(self, event):
        index = self.ctrl.GetSelection()
        setattr(self.prefs, self.attrib_name, self.choices[index])


class ColorPickerField(InfoField):
    same_line = True

    default_width = 100

    def fill_data(self):
        rgba = self.get_value()
        self.ctrl.SetColour(rgba)

    def create_control(self, settings):
        color = (0, 0, 0)
        c = buttons.ColorSelectButton(self.container, -1, "", color, size=(self.default_width, -1), style=wx.BORDER_NONE)
        c.Bind(buttons.EVT_COLORSELECT, self.on_color_changed)
        return c

    def on_color_changed(self, event):
        rgba = event.GetValue()
        color = wx.Colour(rgba)
        setattr(self.prefs, self.attrib_name, color)


class FontComboBox(wx.adv.OwnerDrawnComboBox):
    # Overridden from OwnerDrawnComboBox, called to draw each
    # item in the list
    def OnDrawItem(self, dc, rect, item, flags):
        if item == wx.NOT_FOUND:
            # painting the control, but there is no valid item selected yet
            return

        r = wx.Rect(*rect)  # make a copy
        r.Deflate(3, 5)

        face = fonts.get_font_name(item)
        font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, face)
        dc.SetFont(font)

        if flags & wx.adv.ODCB_PAINTING_CONTROL:
            # for painting the control itself
            dc.DrawText(face, r.x + 5, (r.y + 5) + ((r.height / 2) - dc.GetCharHeight()) / 2)

        else:
            # for painting the items in the popup
            dc.DrawText(face,
                        r.x + 3,
                        (r.y + 5) + ((r.height / 2) - dc.GetCharHeight()) / 2
                        )

    # Overridden from OwnerDrawnComboBox, should return the height
    # needed to display an item in the popup, or -1 for default
    def OnMeasureItem(self, item):
        return 24

    # Overridden from OwnerDrawnComboBox.  Callback for item width, or
    # -1 for default/undetermined
    def OnMeasureItemWidth(self, item):
        return -1  # default - will be measured from text width


class FontField(InfoField):
    default_width = 200

    def fill_data(self):
        font = self.get_value()
        try:
            face = font.GetFaceName()
            index = fonts.get_font_index(face)
            self.ctrl.SetSelection(index)
            size = font.GetPointSize()
            index = fonts.standard_font_sizes.index(size)
            self.size_ctrl.SetSelection(index)
        except RuntimeError as e:
            log.error(f"Failed setting font to {font}: {e}")

    def create_control(self, settings):
        names = fonts.get_font_names()
        c = FontComboBox(self.container, -1, "", size=(self.default_width, -1), choices=names, style=wx.CB_READONLY)
        c.Bind(wx.EVT_COMBOBOX, self.on_face_changed)
        return c

    def create_extra_controls(self, settings):
        names = [str(s) for s in fonts.standard_font_sizes]
        c = wx.ComboBox(self.container, -1, str(fonts.default_font_size), size=(self.default_width/2, -1), choices=names, style=wx.CB_READONLY)
        c.Bind(wx.EVT_COMBOBOX, self.on_size_changed)
        self.size_ctrl = c
        return [c]

    def on_face_changed(self, event):
        self.set_font()

    def on_size_changed(self, event):
        self.set_font()

    def set_font(self):
        index = self.ctrl.GetSelection()
        face = fonts.get_font_name(index)
        index = self.size_ctrl.GetSelection()
        size = fonts.standard_font_sizes[index]
        font = wx.Font(size, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, face)
        setattr(self.prefs, self.attrib_name, font)


class IntRangeField(InfoField):
    default_width = 200

    def fill_data(self):
        value = self.get_value()
        self.ctrl.SetValue(value)

    def get_params(self, settings):
        try:
            lo, hi = settings.split("-")
            lo = int(lo.strip())
            hi = int(hi.strip())
        except:
            lo, hi = 0, 100
        return lo, hi

    def create_control(self, settings):
        minval, maxval = self.get_params(settings)
        c = wx.Slider(self.container, -1, minval, minval, maxval, size=(self.default_width, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        c.Bind(wx.EVT_SLIDER, self.slider_changed)
        return c

    def slider_changed(self, event):
        setattr(self.prefs, self.attrib_name, self.ctrl.GetValue())


class DirectoryField(InfoField):
    same_line = True

    default_width = 400

    def fill_data(self):
        path = self.get_value()
        self.ctrl.SetValue(path, False)

    def create_control(self, settings):
        c = filebrowse.DirBrowseButton(self.container, -1, size=(self.default_width, -1), labelText="", changeCallback = self.on_directory_changed)
        return c

    def on_directory_changed(self, event):
        path = event.GetString()
        setattr(self.prefs, self.attrib_name, path)


known_fields = {
    "int": IntField,
    "intrange": IntRangeField,
    "bool": BoolField,
    "wx.Colour": ColorPickerField,
    "Color": ColorPickerField,
    "wx.Font": FontField,
    "Font": FontField,
    "directory": DirectoryField,
}


def register_preference_field(name, cls):
    global known_fields

    known_fields[name] = cls


def find_field(field_type):
    settings = None
    if ":" in field_type:
        field_type, settings = field_type.split(":", 1)
    try:
        field_cls = known_fields[field_type]
    except TypeError:
        field_cls = ChoiceField
        settings = field_type[:]
    except KeyError:
        log.warning(f"Unknown preference type {field_type}")
        raise
    return field_cls, settings

def calc_field(parent, prefs, attrib_name, field_type, desc):
    field_cls, settings = find_field(field_type)
    log.debug(f"calc_field: {field_type}: {field_cls.__class__.__name__}, {settings}")
    field = field_cls(parent, settings, desc, prefs, attrib_name)
    field.fill_data()
    return field


PANELTYPE = wx.lib.scrolledpanel.ScrolledPanel
class PreferencesPanel(PANELTYPE):
    """
    A panel for displaying and manipulating the properties of a layer.
    """
    LABEL_SPACING = 10
    VALUE_SPACING = 3
    SIDE_SPACING = 5

    window_name = "InfoPanel"

    def __init__(self, parent, prefs, size=(-1,-1)):
        PANELTYPE.__init__(self, parent, name=self.window_name, size=size)
        self.prefs = prefs

        # Mac/Win needs this, otherwise background color is black
        attr = self.GetDefaultAttributes()
        self.SetBackgroundColour(attr.colBg)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.display_panel_for_prefs()

    def display_panel_for_prefs(self):
        self.sizer.AddSpacer(self.LABEL_SPACING)

        prefs = self.prefs
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
            if desc is None:
                desc = attrib_name.replace("_", " ").capitalize()
            if attrib_cls_name is None:
                attrib = getattr(prefs, attrib_name)
                attrib_cls_name = attrib.__class__.__name__
            log.debug(f"{self.prefs._module_path}: {attrib_name}={attrib_cls_name}")

            try:
                field = calc_field(self, prefs, attrib_name, attrib_cls_name, desc)
                self.fields.append(field)
            except KeyError:
                pass

        self.sizer.Layout()

    def get_source_preferences(self):
        pass

    def accept_preferences(self):
        source = self.get_source_preferences()
        if source != self.prefs:
            log.debug(f"preferences updated! {source._module_path}")
            source.copy_from(self.prefs)
            self.prefs.persist_user_settings()


class ApplicationPreferencesPanel(PreferencesPanel):
    def __init__(self, parent, size=(-1,-1)):
        prefs = wx.GetApp().get_preferences().clone()
        PreferencesPanel.__init__(self, parent, prefs, size=size)

    def get_source_preferences(self):
        return wx.GetApp().get_preferences()


class EditorPreferencesPanel(PreferencesPanel):
    def __init__(self, parent, editor, size=(-1,-1)):
        self.editor = editor
        prefs = editor.get_preferences().clone()
        if not prefs.display_order:
            raise RuntimeError("No displayed preferences")
        s = editor.__mro__[1]
        if s.preferences_module == editor.preferences_module:
            raise RuntimeError("Unchanged preferences from superclass")
        PreferencesPanel.__init__(self, parent, prefs, size=size)

    def get_source_preferences(self):
        return self.editor.get_preferences()
