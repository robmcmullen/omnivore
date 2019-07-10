import sys

import wx

from sawx.preferences import SawxEditorPreferences
from sawx.ui.fonts import str_to_font, default_font

from ..editors.byte_editor_preferences import ByteEditorPreferences


class EmulatorPreferences(ByteEditorPreferences):
    def set_defaults(self):
        ByteEditorPreferences.set_defaults(self)
        self.default_emulator = "Atari 800"
