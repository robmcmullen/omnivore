import numpy as np

atascii_to_internal = np.hstack([np.arange(64, 96, dtype=np.uint8),np.arange(64, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
atascii_to_internal = np.hstack([atascii_to_internal, atascii_to_internal + 128])

internal_to_atascii = np.hstack([np.arange(32, 96, dtype=np.uint8),np.arange(32, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
internal_to_atascii = np.hstack([internal_to_atascii, internal_to_atascii + 128])



class ATASCIIFontMapping(object):
    name = "ASCII Order"
    font_mapping = atascii_to_internal

    def __str__(self):
        return self.name

    def __eq__(self, other):
        try:
            return self.name == other.name
        except AttributeError:
            pass
        return False

    # to be usable in dicts, py3 needs __hash__ defined if __eq__ is defined
    def __hash__(self):
        return id(self)

    def wx_char_to_byte(self, char, mods, control):
        import wx
        byte = None

        if mods == wx.MOD_RAW_CONTROL:
            if char == 44:  # Ctrl-, prints ATASCII 0 (heart)
                byte = 0 + control.inverse
            elif char >= 65 and char <= 90:  # Ctrl-[A-Z] prints ATASCII chars 1-26
                byte = char - 64 + control.inverse
            elif char == 46:  # Ctrl-. prints ATASCII 96 (diamond)
                byte = 96 + control.inverse
            elif char == 59:  # Ctrl-; prints ATASCII 123 (spade)
                byte = 123 + control.inverse
            elif char == wx.WXK_TAB:
                byte = 158
            elif char == 50:  # Ctrl-2 prints ATASCII 253 (buzzer)
                byte = 253
            elif char == wx.WXK_INSERT:
                byte = 255
        elif mods == wx.MOD_SHIFT:
            if char == wx.WXK_BACK:
                byte = 156
            elif char == wx.WXK_INSERT:
                byte = 157
            elif char == wx.WXK_TAB:
                byte = 159
        elif char == wx.WXK_HOME:
            byte = 125
        elif char == wx.WXK_BACK:
            byte = 126
        elif char == wx.WXK_TAB:
            byte = 127
        elif char == wx.WXK_RETURN:
            byte = 155
        elif char == wx.WXK_DELETE:
            byte = 254
        elif char == wx.WXK_INSERT:
            byte = 255

        elif control.pending_esc:
            if char == wx.WXK_ESCAPE:
                byte = 27
            elif char == wx.WXK_UP:
                byte = 28
            elif char == wx.WXK_DOWN:
                byte = 29
            elif char == wx.WXK_LEFT:
                byte = 30
            elif char == wx.WXK_RIGHT:
                byte = 31

        elif char == wx.WXK_ESCAPE:
            control.pending_esc = True

        return byte

    def convert_byte_mapping(self, char):
        return char


class AnticFontMapping(ATASCIIFontMapping):
    name = "Antic Order"
    font_mapping = np.arange(256, dtype=np.uint8)

    def convert_byte_mapping(self, char):
        try:
            char = atascii_to_internal[char]
        except IndexError:
            pass
        return char


font_mapping_list = [
    ATASCIIFontMapping(),
    AnticFontMapping(),
]

valid_font_mappings = {mapping.name: mapping for mapping in font_mapping_list}
