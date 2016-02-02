import wx

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
