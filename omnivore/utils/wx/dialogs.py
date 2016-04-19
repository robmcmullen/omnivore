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


class EmulatorDialog(wx.Dialog):
    border = 5
    
    def __init__(self, parent, title, default_emu=None):
        wx.Dialog.__init__(self, parent, -1, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        t = wx.StaticText(self, -1, "Enter emulator informaton:")
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.path = filebrowse.FileBrowseButton(self, -1, size=(450, -1), labelText="Executable:", changeCallback=self.on_path_changed)
        hbox.Add(self.path, 0, wx.LEFT, self.border)
        sizer.Add(hbox, 0, wx.ALL|wx.EXPAND, 0)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, 'Args: ')
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        self.args = wx.TextCtrl(self, -1, size=(-1, -1))
        hbox.Add(self.args, 1, wx.ALL|wx.EXPAND, self.border)
        sizer.Add(hbox, 1, wx.LEFT|wx.RIGHT|wx.TOP|wx.EXPAND, self.border)
        
        t = wx.StaticText(self, -1, "(use %s as placeholder for the data file or it will be added at the end)")
        sizer.Add(t, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, self.border)
        
        t = wx.StaticText(self, -1, " ")
        sizer.Add(t, 0, wx.ALL|wx.EXPAND, self.border)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        t = wx.StaticText(self, -1, 'Display Name: ')
        hbox.Add(t, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, self.border)
        self.name = wx.TextCtrl(self, -1, size=(180, -1))
        hbox.Add(self.name, 0, wx.LEFT, self.border)
        sizer.Add(hbox, 0, wx.ALL|wx.EXPAND, self.border)
        
        self.user_changed = False
        
        btnsizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.SetDefault()
        self.ok_btn.Enable(False)
        btnsizer.AddButton(self.ok_btn)
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        sizer.Add(btnsizer, 1, wx.ALL|wx.EXPAND, self.border)
        
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_TEXT, self.on_name_changed)
        self.SetSizer(sizer)
        
        # Don't call self.Fit() otherwise the dialog buttons are zero height
        sizer.Fit(self)
        
        if default_emu:
            self.set_initial_data(default_emu)

    def on_name_changed(self, evt):
        if evt.GetEventObject() == self.name:
            self.user_changed = True
        elif not self.user_changed:
            self.set_automatic_name()
    
    def set_automatic_name(self):
        name = os.path.basename(self.path.GetValue())
        args = self.args.GetValue()
        if args:
            name += " " + args
        self.name.ChangeValue(name)

    def on_path_changed(self, evt):
        path = evt.GetString()
        if not self.user_changed:
            self.set_automatic_name()
        enabled = bool(which(path))
        self.ok_btn.Enable(enabled)
    
    def on_button(self, evt):
        if evt.GetId() == wx.ID_OK:
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)
        evt.Skip()

    def set_initial_data(self, emu):
        self.user_changed = True
        self.name.ChangeValue(emu['name'])
        self.path.SetValue(emu['exe'])
        self.args.ChangeValue(emu['args'])

    def show_and_get_value(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            emu = {'name': self.name.GetValue(),
                   'exe': self.path.GetValue(),
                   'args': self.args.GetValue(),
                   }
        else:
            emu = None
        self.Destroy()
        return emu

def prompt_for_emulator(parent, title, default_emu=None):
    d = EmulatorDialog(parent, title, default_emu)
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
