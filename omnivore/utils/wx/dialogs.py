import os
import sys
import pickle

import numpy as np
import wx
import wx.lib.filebrowsebutton as filebrowse
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

from omnivore.utils.processutil import which
from omnivore.utils.textutil import text_to_int
from omnivore.utils.wx.dropscroller import ReorderableList, PickledDropTarget, PickledDataObject


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
        except (ValueError, TypeError), e:
            value = None
            error = str(e)
        if return_error:
            return value, error
        else:
            return value

def prompt_for_string(parent, message, title, default=None):
    if default is not None:
        default = str(default)
    else:
        default = ""
    d = SimplePromptDialog(parent, message, title, default)
    return d.show_and_get_value()

def prompt_for_hex(parent, message, title, default=None, return_error=False, default_base="dec"):
    if default is not None:
        default = str(default)
    else:
        default = ""
    d = HexEntryDialog(parent, message, title, default)
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
            self.set_initial_data(default)
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
            control = func(key, label)
            if key is not None:
                self.types[key] = type
                self.controls[key] = control

    def set_initial_data(self, d):
        for key, control in self.controls.iteritems():
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
    
    def get_default_value(self, d, key):
        return d[key]
    
    def get_edited_values(self, d):
        for key, control in self.controls.iteritems():
            type = self.types[key]
            if type == 'text' or type == 'file' or type == 'boolean':
                self.set_output_value(d, key, control.GetValue())
    
    def set_output_value(self, d, key, value):
        d[key] = value
    
    def create_text(self, key, label):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.TextCtrl(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def create_boolean(self, key, label):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.CheckBox(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def create_expando(self, key, label):
        sizer = self.GetSizer()
        status = ExpandoTextCtrl(self, style=wx.ALIGN_LEFT|wx.TE_READONLY|wx.NO_BORDER)
        attr = self.GetDefaultAttributes()
        status.SetBackgroundColour(attr.colBg)
        sizer.Add(status, 1, wx.ALL|wx.EXPAND, self.border)
        return status

    def create_file(self, key, label):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        entry = filebrowse.FileBrowseButton(self, -1, size=(450, -1), labelText=label, changeCallback=self.on_path_changed)
        hbox.Add(entry, 0, wx.LEFT, self.border)
        sizer.Add(hbox, 0, wx.ALL|wx.EXPAND, 0)
        return entry
    
    def create_verify(self, key, label):
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
    
    def create_verify_list(self, key, label):
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

    def create_gauge(self, key, label):
        sizer = self.GetSizer()
        gauge = wx.Gauge(self, -1, 50, size=(500, 5))
        sizer.Add(gauge, 0, wx.ALL|wx.EXPAND, self.border)
        return gauge

    def create_static(self, key, label):
        sizer = self.GetSizer()
        t = wx.StaticText(self, -1, label)
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)

    def create_static_spacer_below(self, key, label):
        sizer = self.GetSizer()
        t = wx.StaticText(self, -1, label)
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)
        t = wx.StaticText(self, -1, " ")
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        
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
        print "Verify!"

    def on_resize(self, event):
        print "resized"
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
            d = dict()
        return d

class ObjectEditDialog(DictEditDialog):
    def __init__(self, parent, title, instructions, fields, object_class, default=None):
        DictEditDialog.__init__(self, parent, title, instructions, fields, default)
        self.new_object_class = object_class
        
    def get_default_value(self, d, key):
        return getattr(d, key)
    
    def get_result_object(self):
        # Edit the object in place by reusing the same dictionary
        if self.default:
            d = self.default
        else:
            d = self.new_object_class()
        return d
    
    def set_output_value(self, d, key, value):
        setattr(d, key, value)


class EmulatorDialog(DictEditDialog):
    border = 5
    
    def __init__(self, parent, title, default=None):
        fields = [
            ('file', 'exe', 'Executable: '),
            ('text', 'args', 'Args: '),
            ('static spacer below', None, "(use %s as placeholder for the data file or it will be added at the end)"),
            ('text', 'name', 'Display Name: '),
            ]
        self.user_changed = False
        DictEditDialog.__init__(self, parent, title, "Enter emulator information:", fields, default)

    def on_text_changed(self, evt):
        if evt.GetEventObject() == self.controls['name']:
            self.user_changed = True
        elif not self.user_changed:
            self.set_automatic_name()
    
    def set_automatic_name(self):
        name = os.path.basename(self.controls['exe'].GetValue())
        args = self.controls['args'].GetValue()
        if args:
            name += " " + args
        self.controls['name'].ChangeValue(name)

    def on_path_changed(self, evt):
        if not self.user_changed:
            self.set_automatic_name()
        self.ok_btn.Enable(self.can_submit())
        
    def can_submit(self):
        path = self.controls['exe'].GetValue()
        return bool(which(path))

def prompt_for_emulator(parent, title, default_emu=None):
    d = EmulatorDialog(parent, title, default_emu)
    return d.show_and_get_value()


class AssemblerDialog(DictEditDialog):
    border = 5
    
    def __init__(self, parent, title, default=None):
        fields = [
            ('text', 'name', 'Name: '),
            ('text', 'origin', 'Origin Directive: '),
            ('text', 'data byte', 'Data Byte Directive: '),
            ('text', 'comment char', 'Comment Char: '),
            ]
        DictEditDialog.__init__(self, parent, title, "Enter assembler information:", fields, default)
    
    def can_submit(self):
        control = self.controls['name']
        return len(control.GetValue()) > 0

def prompt_for_assembler(parent, title, default=None):
    d = AssemblerDialog(parent, title, default)
    return d.show_and_get_value()


def get_file_dialog_wildcard(name, extension_list):
    # Using only the first extension
    wildcards = []
    if extension_list:
        ext = extension_list[0]
        wildcards.append("%s (*%s)|*%s" % (name, ext, ext))
    return "|".join(wildcards)


class SegmentOrderDialog(wx.Dialog):
    border = 5
    instructions = "Drag segments to the right-hand list to create an executable"
    
    def __init__(self, parent, title, segments):
        wx.Dialog.__init__(self, parent, -1, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        self.segment_map = {k:v for k,v in enumerate(segments)}
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
        t = wx.StaticText(self, -1, self.instructions)
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        t = wx.StaticText(self, -1, "All Segments")
        vbox1.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        self.source = ReorderableList(self, self.segment_map.keys(), self.get_item_text, columns=["Origin", "Size", "Name"], resize_column=3, allow_drop=False, size=(400,300))
        vbox1.Add(self.source, 1, wx.ALL|wx.EXPAND, self.border)
        hbox.Add(vbox1, 1, wx.ALL|wx.EXPAND, 0)

        vbox2 = wx.BoxSizer(wx.VERTICAL)
        t = wx.StaticText(self, -1, "Segments In Executable")
        vbox2.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        self.dest = ReorderableList(self, [], self.get_item_text, columns=["Origin", "Size", "Name"], resize_column=3, size=(400,300))
        vbox2.Add(self.dest, 1, wx.ALL|wx.EXPAND, self.border)
        hbox.Add(vbox2, 1, wx.ALL|wx.EXPAND, 0)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        t = wx.StaticText(self, -1, "Run Address")
        vbox.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        self.run_addr = wx.TextCtrl(self, -1, size=(-1, -1))
        vbox.Add(self.run_addr, 0, wx.ALL|wx.EXPAND, self.border)
        
        vbox.AddSpacer(50)
        
        self.clear = b = wx.Button(self, wx.ID_DOWN, 'Clear List', size=(90, -1))
        b.Bind(wx.EVT_BUTTON, self.on_clear)
        vbox.Add(b, 0, wx.ALL|wx.EXPAND, self.border)
        
        vbox.AddStretchSpacer()
        
        btnsizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.SetDefault()
        btnsizer.AddButton(self.ok_btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        vbox.Add(btnsizer, 0, wx.ALL|wx.EXPAND, self.border)
        hbox.Add(vbox, 0, wx.EXPAND, 0)
        sizer.Add(hbox, 1, wx.EXPAND, 0)
        
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_TEXT, self.on_text_changed)
        
        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)
        self.check_enable()
    
    def get_item_text(self, sid):
        s = self.segment_map[sid]
        return "%x" % s.start_addr, "%x" % len(s), s.name
        
    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def on_text_changed(self, evt):
        self.ok_btn.Enable(self.can_submit())

    def on_clear(self, evt):
        self.dest.clear()

    def on_resize(self, event):
        print "resized"
        self.Fit()
    
    def get_run_addr(self):
        text = self.run_addr.GetValue()
        try:
            addr = text_to_int(text, "hex")
            if addr < 0 or addr > 0xffff:
                addr = None
        except (ValueError, TypeError), e:
            addr = None
        return addr
    
    def can_submit(self):
        return self.get_run_addr() is not None and self.dest.GetItemCount() > 0
    
    def check_enable(self):
        self.ok_btn.Enable(self.can_submit())
    
    def get_segments(self):
        s = []
        for sid in self.dest.items:
            s.append(self.segment_map[sid])
        return s

    def get_bytes(self):
        segments = self.get_segments()
        total = 2
        for s in segments:
            total += 4 + len(s)
        total += 6
        bytes = np.zeros([total], dtype=np.uint8)
        bytes[0:2] = 0xff # FFFF header
        i = 2
        for s in segments:
            words = bytes[i:i+4].view(dtype='<u2')
            words[0] = s.start_addr
            words[1] = s.start_addr + len(s) - 1
            i += 4
            bytes[i:i + len(s)] = s[:]
            i += len(s)
        words = bytes[i:i+6].view(dtype='<u2')
        words[0] = 0x2e0
        words[1] = 0x2e1
        words[2] = self.get_run_addr()
        return bytes


class ListReorderDialog(wx.Dialog):
    """Simple dialog to return a list of items that can be reordered by the user.
    """
    border = 5
    
    def __init__(self, parent, items, get_item_text, dialog_helper=None, title="Reorder List", copy_helper=None):
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
        
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.delete_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.on_delete, id=self.delete_id)
        
        self.get_item_text = get_item_text
        self.dialog_helper = dialog_helper
        self.copy_helper = copy_helper
        self.on_list_selection(None)
    
    def on_list_selection(self, evt):
        self.up.Enable(self.list.can_move_up)
        self.down.Enable(self.list.can_move_down)
        state = self.list.GetSelectedItemCount() > 0
        self.edit.Enable(state)
        if self.copy is not None:
            self.copy.Enable(state)
        self.delete.Enable(state)
    
    def on_context_menu(self, evt):
        menu = wx.Menu()
        menu.Append(wx.ID_NEW, "New Item")
        menu.Append(wx.ID_EDIT, "Edit Item")
        if self.copy is not None:
            menu.Append(wx.ID_COPY, "Copy Item")
        menu.Append(wx.ID_DELETE, "Delete Selected Items")
        if self.list.GetSelectedItemCount() == 0:
            menu.Enable(wx.ID_EDIT, False)
            if self.copy is not None:
                menu.Enable(wx.ID_COPY, False)
            menu.Enable(wx.ID_DELETE, False)
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
    
    def on_delete(self, evt):
        self.list.delete_selected()


if __name__ == "__main__":
    app = wx.PySimpleApp()

    frame = wx.Frame(None, -1, "Dialog test")
#    dialog = EmulatorDialog(frame, "Test")
#    dialog.ShowModal()
    dlg = ListReorderDialog(frame, [chr(i + 65) for i in range(26)], lambda a:str(a))
    if dlg.ShowModal() == wx.ID_OK:
        print dlg.get_items()
    dlg.Destroy()

    app.MainLoop()
