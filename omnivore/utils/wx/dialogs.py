import wx

class HexEntryDialog(wx.TextEntryDialog):
    """Simple subclass of wx.TextEntryDialog to convert text result from
    hexidecimal if necessary.
    """
    def get_int(self):
        text = self.GetValue()
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

    def show_and_get_value(self):
        result = self.ShowModal()
        if result == wx.ID_OK:
            value = self.get_int()
        else:
            value = None
        self.Destroy()
        return value
