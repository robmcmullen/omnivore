import os

import wx
import wx.lib.filebrowsebutton as filebrowse

from omnivore.utils.processutil import which


class SimplePromptDialog(wx.TextEntryDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result to a
    specific format
    """
    def convert_text(self, text):
        return text

    def show_and_get_value(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            text = self.GetValue()
            value = self.convert_text(text)
        else:
            value = None
        self.Destroy()
        return value

class HexEntryDialog(SimplePromptDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result from
    hexidecimal if necessary.
    """
    def convert_text(self, text):
        try:
            if text.startswith("0x"):
                value = int(text[2:], 16)
            elif text.startswith("$"):
                value = int(text[1:], 16)
            else:
                value = int(text)
        except (ValueError, TypeError):
            value = None
        return value

def prompt_for_string(parent, message, title, default=None):
    if default is not None:
        default = str(default)
    else:
        default = ""
    d = SimplePromptDialog(parent, message, title, default)
    return d.show_and_get_value()

def prompt_for_hex(parent, message, title, default=None):
    if default is not None:
        default = str(default)
    else:
        default = ""
    d = HexEntryDialog(parent, message, title, default)
    if default:
        d.SetValue(default)
    return d.show_and_get_value()


class DictEditDialog(wx.Dialog):
    border = 5
    
    def __init__(self, parent, title, instructions, fields, default=None):
        wx.Dialog.__init__(self, parent, -1, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
        t = wx.StaticText(self, -1, instructions)
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        
        self.controls = {}
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
        
        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)
        
        self.default = default
        if default:
            self.set_initial_data(default)
        self.ok_btn.Enable(self.can_submit())
    
    def add_fields(self, fields):
        for type, key, label in fields:
            if type == 'text':
                control = self.create_text(label)
            elif type == 'file':
                control = self.create_file(label)
            elif type == 'static spacer below':
                control = self.create_static_spacer_below(label)
            else:
                raise NotImplementedError("Unknown field type %s for %s" % (type, key))
            if key is not None:
                self.controls[key] = type, control

    def set_initial_data(self, d):
        for key, (type, control) in self.controls.iteritems():
            if type == 'text':
                control.ChangeValue(d[key])
            elif type == 'file':
                control.SetValue(d[key])
    
    def get_edited_values(self, d):
        for key, (type, control) in self.controls.iteritems():
            if type == 'text' or type == 'file':
                d[key] = control.GetValue()
    
    def create_text(self, label):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, label)
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        entry = wx.TextCtrl(self, -1, size=(-1, -1))
        hbox.Add(entry, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 1, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        return entry

    def create_file(self, label):
        sizer = self.GetSizer()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        entry = filebrowse.FileBrowseButton(self, -1, size=(450, -1), labelText=label, changeCallback=self.on_path_changed)
        hbox.Add(entry, 0, wx.LEFT, self.border)
        sizer.Add(hbox, 0, wx.ALL|wx.EXPAND, 0)
        return entry

    def create_static_spacer_below(self, label):
        sizer = self.GetSizer()
        t = wx.StaticText(self, -1, label)
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)
        t = wx.StaticText(self, -1, " ")
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
    
    def get_control(self, key):
        type, control = self.controls[key]
        return control
        
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
    
    def can_submit(self):
        return True

    def show_and_get_value(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            # Edit the object in place by reusing the same dictionary
            if self.default:
                d = self.default
            else:
                d = dict()
            self.get_edited_values(d)
        else:
            d = None
        self.Destroy()
        return d


class EmulatorDialog(DictEditDialog):
    border = 5
    
    def __init__(self, parent, title, default=None):
        fields = [
            ('file', 'exe', 'Executable: '),
            ('text', 'args', 'Args: '),
            ('static spacer below', None, "(use %s as placeholder for the data file or it will be added at the end)"),
            ('text', 'name', 'Display Name: '),
            ]
        DictEditDialog.__init__(self, parent, title, "Enter emulator information:", fields, default)
        
        self.user_changed = False

    def on_text_changed(self, evt):
        if evt.GetEventObject() == self.get_control('name'):
            self.user_changed = True
        elif not self.user_changed:
            self.set_automatic_name()
    
    def set_automatic_name(self):
        name = os.path.basename(self.get_control('exe').GetValue())
        args = self.get_control('args').GetValue()
        if args:
            name += " " + args
        self.get_control('name').ChangeValue(name)

    def on_path_changed(self, evt):
        if not self.user_changed:
            self.set_automatic_name()
        self.ok_btn.Enable(self.can_submit())
        
    def can_submit(self):
        path = self.get_control('exe').GetValue()
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
        type, control = self.controls['name']
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

if __name__ == "__main__":
    app = wx.PySimpleApp()

    frame = wx.Frame(None, -1, "Dialog test")
    dialog = EmulatorDialog(frame, "Test")
    dialog.ShowModal()

    app.MainLoop()
