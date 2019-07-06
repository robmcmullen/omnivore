import os
import sys
import pickle

import numpy as np
import wx
import wx.lib.filebrowsebutton as filebrowse
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

from .. import art
from ..utils.processutil import which
from ..utils.textutil import text_to_int
from .dropscroller import ReorderableList, PickledDropTarget, PickledDataObject

import logging
log = logging.getLogger(__name__)


class SimplePromptDialog(wx.TextEntryDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result to a
    specific format
    """

    def convert_text(self, text, return_error=False, **kwargs):
        if return_error:
            return text, ""
        else:
            return text

    def show_and_get_value(self, return_error=False, **kwargs):
        result = self.ShowModal()
        if result == wx.ID_OK:
            text = self.GetValue()
            value = self.convert_text(text, return_error, **kwargs)
        else:
            if return_error:
                value = None, "Cancelled"
            else:
                value = None
        self.Destroy()
        return value


class HexEntryDialog(SimplePromptDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result from
    hexidecimal if necessary.
    """

    def convert_text(self, text, return_error=False, default_base="dec", **kwargs):
        try:
            value = text_to_int(text, default_base)
            error = ""
        except (ValueError, TypeError) as e:
            value = None
            error = str(e)
        if return_error:
            return value, error
        else:
            return value


class SliceEntryDialog(SimplePromptDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result from
    hexidecimal if necessary.
    """

    def convert_text(self, text, return_error=False, default_base="dec", **kwargs):
        try:
            if "," in text:
                start, extra = text.split(",")
                if "," in extra:
                    end, step = extra.split(",")
                else:
                    end = extra
                    step = "1"
            else:
                start = text
                end = "-1"
                step = "1"
            start = text_to_int(start, default_base)
            end = text_to_int(end, default_base)
            step = text_to_int(step, default_base)
            error = ""
        except (ValueError, TypeError) as e:
            start, end, step = None, None, None
            error = str(e)
        if return_error:
            return None, error
        else:
            return slice(start, end, step)


def prompt_for_string(parent, message, title, default=None):
    if default is not None:
        default = str(default)
    else:
        default = ""
    d = SimplePromptDialog(parent, message, title, default)
    return d.show_and_get_value()


def prompt_for_hex(parent, message, title, default=None, return_error=False, default_base="hex"):
    if default is not None:
        if default_base == "hex":
            default = hex(int(default))[2:]
        else:
            default = str(int(default))
    else:
        default = ""
    d = HexEntryDialog(parent, message, title, default)
    if default:
        d.SetValue(default)
    return d.show_and_get_value(return_error=return_error, default_base=default_base)


def prompt_for_dec(parent, message, title, default=None, return_error=False, default_base="dec"):
    return prompt_for_hex(parent, message, title, default, return_error, default_base)


def prompt_for_slice(parent, message, title, default=None, return_error=False, default_base="hex"):
    if default is not None:
        if default_base == "hex":
            default = hex(int(default))[2:]
        else:
            default = str(int(default))
    else:
        default = ""
    d = SliceEntryDialog(parent, message, title, default)
    if default:
        d.SetValue(default)
    return d.show_and_get_value(return_error=return_error, default_base=default_base)


class DictEditDialog(wx.Dialog):
    border = 5

    def __init__(self, parent, title, instructions, fields, default=None):
        wx.Dialog.__init__(self, parent, -1, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        t = wx.StaticText(self, -1, instructions)
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)

        self.types = {}
        self.controls = {}
        self.buttons = {}
        self.add_fields(fields)

        btnsizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.SetDefault()
        btnsizer.AddButton(self.ok_btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 1, wx.ALL|wx.EXPAND, self.border)

        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_TEXT, self.on_text_changed)
        self.Bind(EVT_ETC_LAYOUT_NEEDED, self.on_resize)

        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)

        self.default = default
        if default:
            self.set_initial_values(default)
        self.check_enable()

    def add_fields(self, fields):
        """ Calls the create_X method where X is the type of the field. Fields
        are a list of tuples: (type, key, label) or (type, key, label, choices)
        """
        for field in fields:
            try:
                type, key, label = field
                choices = None
            except ValueError:
                type, key, label, choices = field
            try:
                func = getattr(self, "create_%s" % type.replace(" ", "_"))
            except AttributeError:
                raise NotImplementedError("Unknown field type %s for %s" % (type, key))
            control = func(key, label, choices)
            if key is not None:
                self.types[key] = type
                self.controls[key] = control

    def set_initial_values(self, d):
        for key in list(self.controls.keys()):
            self.set_initial_value_of(d, key)

    def set_initial_value_of(self, d, key):
        control = self.controls[key]
        type = self.types[key]
        if type == 'text' or type == 'verify':
            value = self.get_default_value(d, key)
            control.ChangeValue(value)
        elif type == 'verify list':
            value = "\n".join(self.get_default_value(d, key))
            control.ChangeValue(value)
        elif type == 'file' or type == 'boolean':
            value = self.get_default_value(d, key)
            control.SetValue(value)
        elif type == 'dropdown':
            value = self.get_default_value(d, key)
            control.SetStringSelection(value)

    def get_default_value(self, d, key):
        return d[key]

    def get_edited_values(self, d):
        for key in list(self.controls.keys()):
            self.get_edited_value_of(d, key)

    def get_edited_value_of(self, d, key):
        control = self.controls[key]
        type = self.types[key]
        try:
            if type == 'verify list':
                value = control.GetValue().splitlines()
            elif type == 'dropdown':
                value = control.GetStringSelection()
            else:
                value = control.GetValue()
            self.set_output_value(d, key, value)
        except AttributeError:
            log.error("Error setting output value for %s %s" % (key, control))

    def set_output_value(self, d, key, value):
        d[key] = value

    def create_text(self, key, label, choices=None):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.TextCtrl(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def create_boolean(self, key, label, choices=None):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.CheckBox(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def create_expando(self, key, label, choices=None):
        sizer = self.GetSizer()
        status = ExpandoTextCtrl(self, style=wx.ALIGN_LEFT|wx.TE_READONLY|wx.NO_BORDER)
        attr = self.GetDefaultAttributes()
        status.SetBackgroundColour(attr.colBg)
        sizer.Add(status, 1, wx.ALL|wx.EXPAND, self.border)
        return status

    def create_file(self, key, label, choices=None):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        entry = filebrowse.FileBrowseButton(self, -1, size=(450, -1), labelText=label, changeCallback=self.on_path_changed)
        hbox.Add(entry, 0, wx.LEFT, self.border)
        sizer.Add(hbox, 0, wx.ALL|wx.EXPAND, 0)
        return entry

    def create_verify(self, key, label, choices=None):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.TextCtrl(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        verify = wx.Button(self, -1, "Verify")
        hbox.Add(verify, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND|wx.ALIGN_CENTER, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        verify.Bind(wx.EVT_BUTTON, self.on_verify)
        self.buttons[key] = verify
        return entry

    def create_verify_list(self, key, label, choices=None):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.TextCtrl(self, -1, size=(-1, 100), style=wx.TE_MULTILINE|wx.HSCROLL)
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        verify = wx.Button(self, -1, "Verify")
        hbox.Add(verify, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        verify.Bind(wx.EVT_BUTTON, self.on_verify)
        self.buttons[key] = verify
        return entry

    def create_gauge(self, key, label, choices=None):
        sizer = self.GetSizer()
        gauge = wx.Gauge(self, -1, 50, size=(500, 5))
        sizer.Add(gauge, 0, wx.ALL|wx.EXPAND, self.border)
        return gauge

    def create_static(self, key, label, choices=None):
        sizer = self.GetSizer()
        t = wx.StaticText(self, -1, label)
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)

    def create_static_spacer_below(self, key, label, choices=None):
        sizer = self.GetSizer()
        t = wx.StaticText(self, -1, label)
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)
        t = wx.StaticText(self, -1, " ")
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)

    def create_dropdown(self, key, label, choices):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.Choice(self, -1, choices=choices, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def on_text_changed(self, evt):
        self.ok_btn.Enable(self.can_submit())

    def on_path_changed(self, evt):
        pass

    def on_verify(self, evt):
        pass

    def on_resize(self, event):
        self.Fit()

    def can_submit(self):
        return True

    def check_enable(self):
        self.ok_btn.Enable(self.can_submit())

    def show_and_get_value(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            d = self.get_result_object()
            self.get_edited_values(d)
        else:
            d = None
        self.Destroy()
        return d

    def get_result_object(self):
        # Edit the object in place by reusing the same dictionary
        if self.default:
            d = self.default
        else:
            d = self.get_new_object()
        return d

    def get_new_object(self):
        return dict()


class ObjectEditDialog(DictEditDialog):
    def __init__(self, parent, title, instructions, fields, object_class, default=None):
        DictEditDialog.__init__(self, parent, title, instructions, fields, default)
        self.new_object_class = object_class

    def get_default_value(self, d, key):
        return getattr(d, key)

    def get_new_object(self):
        return self.new_object_class()

    def set_output_value(self, d, key, value):
        setattr(d, key, value)


def get_file_dialog_wildcard(extension_list):
    wildcards = []
    for item in extension_list:
        name = item[0]
        exts = item[1:]
        ext = ";".join(["*" + e for e in exts])
        wildcards.append("%s (%s)|%s" % (name, ext, ext))
    return "|".join(wildcards)


class ListReorderDialog(wx.Dialog):
    """Simple dialog to return a list of items that can be reordered by the user.
    """
    border = 5

    def __init__(self, parent, items, get_item_text, dialog_helper=None, title="Reorder List", copy_helper=None, default_helper=None):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.list = ReorderableList(self, items, get_item_text, size=(-1,500))
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_selection)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_list_selection)
        sizer.Add(self.list, 1, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.up = b = wx.Button(self, wx.ID_UP, 'Up', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_up)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)

        self.down = b = wx.Button(self, wx.ID_DOWN, 'Down', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_down)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)

        vbox.AddSpacer(50)

        b = wx.Button(self, wx.ID_NEW, 'New', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_new)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)

        self.edit = b = wx.Button(self, wx.ID_EDIT, 'Edit', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_edit)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)

        if copy_helper is not None:
            self.copy = b = wx.Button(self, wx.ID_COPY, 'Copy', size=(90, -1))
            b.Bind(wx.EVT_BUTTON, self.on_copy)
            vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)
        else:
            self.copy = None

        if default_helper is not None:
            self.default = b = wx.Button(self, wx.ID_COPY, 'Set as Default', size=(90, -1))
            b.Bind(wx.EVT_BUTTON, self.on_set_default)
            vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)
        else:
            self.default = None
        self.default_helper = default_helper

        vbox.AddSpacer(50)

        self.delete = b = wx.Button(self, wx.ID_DELETE, 'Delete', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_delete)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)

        vbox.AddStretchSpacer()

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        vbox.Add(btnsizer, 0, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(vbox, 0, wx.EXPAND, 0)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

        self.list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.delete_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.on_delete, id=self.delete_id)

        self.get_item_text = get_item_text
        self.dialog_helper = dialog_helper
        self.copy_helper = copy_helper
        self.on_list_selection(None)

    def on_list_selection(self, evt):
        one_selected = self.list.GetSelectedItemCount() == 1
        any_selected = self.list.GetSelectedItemCount() > 0
        self.up.Enable(self.list.can_move_up)
        self.down.Enable(self.list.can_move_down)
        self.edit.Enable(one_selected)
        if self.copy is not None:
            self.copy.Enable(one_selected)
        if self.default is not None:
            self.default.Enable(one_selected)
        self.delete.Enable(any_selected)

    def on_context_menu(self, evt):
        one_selected = self.list.GetSelectedItemCount() == 1
        any_selected = self.list.GetSelectedItemCount() > 0
        menu = wx.Menu()
        menu.Append(wx.ID_NEW, "New Item")
        menu.Append(wx.ID_EDIT, "Edit Item")
        menu.Enable(wx.ID_EDIT, one_selected)
        if self.copy is not None:
            menu.Append(wx.ID_COPY, "Copy Item")
            menu.Enable(wx.ID_COPY, one_selected)
        menu.AppendSeparator()
        menu.Append(wx.ID_SELECTALL, "Select All")
        menu.Append(wx.ID_CLEAR, "Deselect All")
        menu.Append(wx.ID_DELETE, "Delete Selected Items")
        menu.Enable(wx.ID_DELETE, any_selected)
        id = self.GetPopupMenuSelectionFromUser(menu)
        menu.Destroy()
        if id == wx.ID_NEW:
            self.on_new(evt)
        elif id == wx.ID_DELETE:
            self.on_delete(evt)
        elif id == wx.ID_EDIT:
            self.on_edit(evt)
        elif id == wx.ID_COPY:
            self.on_copy(evt)
        if id == wx.ID_SELECTALL:
            self.list.select_all()
        elif id == wx.ID_CLEAR:
            self.list.deselect_all()

    def get_items(self):
        return self.list.items

    def on_up(self, evt):
        if self.list.can_move_up:
            self.list.move_selected(-1)

    def on_down(self, evt):
        if self.list.can_move_down:
            self.list.move_selected(1)

    def on_new(self, evt):
        new_item = self.dialog_helper(self, "Add Item")
        if new_item is not None:
            self.insert_new_item(new_item)

    def insert_new_item(self, new_item):
        index = self.list.GetFirstSelected()
        if index == -1:
            index = len(self.list.items)
        else:
            index += 1
        self.list.items[index:index] = [new_item]
        self.list.refresh()
        self.list.deselect_all()
        self.list.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    def on_edit(self, evt):
        index = self.list.GetFirstSelected()
        if index >= 0:
            item = self.list.items[index]
            new_item = self.dialog_helper(self, "Edit %s" % self.get_item_text(item), item)
            if new_item is not None:
                self.list.items[index] = new_item
                self.list.refresh()

    def on_copy(self, evt):
        index = self.list.GetFirstSelected()
        if index >= 0:
            item = self.list.items[index]
            new_item = self.copy_helper(item)
            if new_item is not None:
                self.insert_new_item(new_item)

    def on_set_default(self, evt):
        index = self.list.GetFirstSelected()
        if index >= 0:
            for i, item in enumerate(self.list.items):
                self.default_helper(item, i == index)
            self.list.refresh()

    def on_delete(self, evt):
        self.list.delete_selected()


class CheckItemDialog(wx.Dialog):
    """Simple dialog to return a list of items that can be reordered by the user.
    """
    border = 5

    def __init__(self, parent, items, get_item_text, dialog_helper=None, title="Select Items", instructions=""):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.get_item_text = get_item_text
        self.dialog_helper = dialog_helper

        if instructions:
            t = wx.StaticText(self, -1, instructions)
            sizer.Add(t, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, self.border)

        # Use multi-select to make sure no initial item is selecte. Single
        # select forces the first item to be selected.
        self.list = wx.CheckListBox(self, size=(-1,500), style=wx.LB_MULTIPLE)

        # Both EVT_LISTBOX and EVT_CHECKLISTBOX cancel each other out when
        # clicking on the check box itself. Clicking only on item text causes
        # EVT_LISTBOX event only.
#        self.list.Bind(wx.EVT_LISTBOX, self.on_list_selection)
        self.list.Bind(wx.EVT_CHECKLISTBOX, self.on_list_check)
        self.list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.set_items(items)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.EXPAND, 0)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.delete_id = wx.NewId()

    def set_items(self, items):
        self.clear()
        for item in items:
            self.insert_item(self.list.GetCount(), item)

    def insert_item(self, index, item):
        self.list.Insert("placeholder", index)
        self.set_item_text(index, item)
        self.items[index:index] = [item]

    def set_item_text(self, index, item):
        text = self.get_item_text(item)
        self.list.SetString(index, text)

    def on_list_selection(self, evt):
        index = evt.GetInt()
        self.list.Check(index, not self.list.IsChecked(index))
        self.list.SetSelection(index)

    def on_list_check(self, evt):
        index = evt.GetInt()

    def on_context_menu(self, evt):
        menu = wx.Menu()
        menu.Append(wx.ID_SELECTALL, "Select All")
        menu.Append(wx.ID_CLEAR, "Deselect All")
        id = self.GetPopupMenuSelectionFromUser(menu)
        menu.Destroy()
        if id == wx.ID_SELECTALL:
            self.select_all()
        elif id == wx.ID_CLEAR:
            self.deselect_all()

    def select_all(self):
        self.list.SetChecked(list(range(self.list.GetCount())))

    def deselect_all(self):
        self.list.SetChecked([])

    def get_items(self):
        return self.items

    def get_checked_items(self):
        return [self.items[i] for i in self.list.GetCheckedItems()]

    def clear(self, evt=None):
        self.list.Clear()
        self.items = []


class ChooseOnePlusCustomDialog(wx.Dialog):
    """Simple dialog to return a choice from a list or a custom value
    """
    border = 5

    def __init__(self, parent, items, default=None, default_custom_value="", title="Select Items", instructions="", custom_value_label="Custom Value"):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)

        if instructions:
            t = wx.StaticText(self, -1, instructions)
            sizer.Add(t, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, self.border)

        # custom item will be last in the list
        self.custom_item_index = len(items)
        items.append("Custom")

        self.list = wx.ListBox(self, choices=items, size=(-1,200), style=wx.LB_SINGLE)
        try:
            index = items.index(default)
        except ValueError:
            if default_custom_value:
                index = self.custom_item_index
            else:
                index = 0
        self.list.SetSelection(index)

        # Both EVT_LISTBOX and EVT_CHECKLISTBOX cancel each other out when
        # clicking on the check box itself. Clicking only on item text causes
        # EVT_LISTBOX event only.
        self.list.Bind(wx.EVT_LISTBOX, self.on_list_selection)
        sizer.Add(self.list, 1, wx.EXPAND)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, custom_value_label + ":")
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        self.custom_value = wx.TextCtrl(self, -1, default_custom_value, size=(-1, -1))
        hbox.Add(self.custom_value, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.EXPAND)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 0, wx.EXPAND, 0)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

    def on_list_selection(self, evt):
        index = evt.GetInt()
        if index == self.custom_item_index:
            wx.CallAfter(self.custom_value.SetFocus)
            self.custom_value.Enable(True)
        else:
            self.custom_value.Enable(False)
        evt.Skip()

    def get_selected(self):
        index = self.list.GetSelection()
        if index == self.custom_item_index:
            # custom value
            label = None
            custom = self.custom_value.GetValue()
        else:
            label = self.list.GetString(index)
            custom = None
        return label, custom


class HtmlAboutDialog(wx.Dialog):
    """Simple 'About' dialog with an image on the left and HTML text on
    the right.
    """
    border = 20

    def __init__(self, parent, title, html, bitmap):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.SetBackgroundColour("#222255")
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.bitmap = wx.StaticBitmap(self, -1, bitmap)
        sizer.Add(self.bitmap, 0, wx.ALIGN_TOP|wx.ALL, self.border)

        self.html = wx.html.HtmlWindow(self, -1, size=(400, 400))
        self.html.SetPage(html)
        sizer.Add(self.html, 1, wx.EXPAND|wx.ALL, 0)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_clicked)

    def on_activate(self, evt):
        log.debug(f"on_link_clicked: {evt.GetActive()}")
        if not evt.GetActive():
            wx.CallAfter(self.Destroy)

    def on_link_clicked(self, evt):
        href = evt.GetLinkInfo().GetHref()
        log.debug(f"on_link_clicked: {href}")


class SawxAboutDialog(HtmlAboutDialog):
    @classmethod
    def is_shown(cls):
        for frame in wx.GetTopLevelWindows():
            if isinstance(frame, HtmlAboutDialog):
                return frame
        return None

    @classmethod
    def show_or_raise(cls):
        frame = cls.is_shown()
        if frame:
            frame.Raise()
        else:
            frame = cls()

    def __init__(self):
        app = wx.GetApp()
        bitmap = art.get_bitmap(app.about_dialog_image)
        html = app.about_dialog_html
        HtmlAboutDialog.__init__(self, None, app.app_name, html, bitmap)
        wx.CallAfter(self.Show)


if __name__ == "__main__":
    app = wx.PySimpleApp()

    frame = wx.Frame(None, -1, "Dialog test")
#    dialog = EmulatorDialog(frame, "Test")
#    dialog.ShowModal()
#    dlg = ListReorderDialog(frame, [chr(i + 65) for i in range(26)], lambda a:str(a))
    # dlg = CheckItemDialog(frame, [chr(i + 65) for i in range(26)], lambda a:str(a))
    # if dlg.ShowModal() == wx.ID_OK:
    #     print dlg.get_checked_items()
    # dlg = ChooseOnePlusCustomDialog(frame, ["one", "two"], "instructions")
    # if dlg.ShowModal() == wx.ID_OK:
    #     print "Selected", dlg.get_selected()
    # dlg.Destroy()

    class TestObj(object):
        def __init__(self):
            self.name = "aoeu"
            self._state = False

        @property
        def state(self):
            return 'state true' if self._state else 'state false'

        @state.setter
        def state(self, value):
            print(("Setting to:", value))
            self._state = (value == 'state true')

    class TestSetattrDialog(ObjectEditDialog):
        def __init__(self, parent, title, default=None):
            fields = [
                ('text', 'name', 'Server Name: '),
                ('dropdown', 'state', 'State choice', ['state true', 'state false']),
                ]
            ObjectEditDialog.__init__(self, parent, title, "Setattr test", fields, TestObj, default)

    test_obj = TestObj()
    dlg = TestSetattrDialog(frame, "Test", test_obj)
    dlg.show_and_get_value()
    print((test_obj.state))
    dlg = TestSetattrDialog(frame, "Test", test_obj)
    dlg.show_and_get_value()
    print((test_obj.state))

    app.MainLoop()
