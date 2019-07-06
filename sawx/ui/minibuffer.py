import os
import re

import wx
import wx.lib.buttons as buttons

from .buttons import FlatBitmapToggleButton
from .zoomruler import ZoomRuler

import logging
log = logging.getLogger(__name__)

# Placeholder for i18n
_ = str


class Minibuffer(object):
    """
    Base class for an action that is implemented using the minibuffer.
    Minibuffer is a concept from emacs where, instead of popping up a
    dialog box, uses the bottom of the screen as a small user input
    window.
    """
    label = "Input:"
    error = "Bad input."
    show_close_button = True

    def __init__(self, editor, command_cls, label=None, initial=None, help_text=None, help_tip=None, **kwargs):
        self.control = None
        self.editor = editor
        self.command_cls = command_cls
        if label is not None:
            self.label = label
        elif self.command_cls is not None:
            self.label = command_cls.ui_name
        self.initial = initial
        self.help_text = help_text
        self.help_tip = help_tip
        self.kwargs = kwargs

    def change_editor(self, editor):
        self.editor = editor

    def create_control(self, parent, **kwargs):
        """ Creates the minibuffer in a panel and returns the panel to be
        managed by the minibuffer controller.

        There are three methods that can be overridden in subclasses to provide
        a bit of reusability: create_header_controls, create_primary_control,
        create_footer_controls.

        Or you can just override this method and do it all yourself.
        """
        self.control = wx.Panel(parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.create_header_controls(self.control, sizer)
        self.create_primary_control(self.control, sizer)
        self.create_footer_controls(self.control, sizer)

        self.control.SetSizer(sizer)
        self.control.Fit()

        self.set_best_size()

        self.post_create()

    def create_primary_control(self, parent, sizer):
        """ Creates the major editing component in the minibuffer

        """
        self.control.SetBackgroundColour('blue')

    def create_header_controls(self, parent, sizer):
        """ Hook to creates auxiliary controls

        """
        pass

    def create_footer_controls(self, parent, sizer):
        """ Hook to creates auxiliary controls

        """
        pass

    def set_best_size(self):
        pass

    def post_create(self):
        """ Hook to set up the controls after all of them have been created.

        """
        pass

    def destroy_control(self):
        if self.control is not None:
            self.control.Destroy()
            self.control = None

    def focus(self):
        """
        Set the focus to the component in the menubar that should get
        the text focus.
        """
        log.debug("focus!!!")
        self.control.SetFocus()

    def perform(self):
        """Execute the command associatied with this minibuffer"""
        pass

    def is_repeat(self, other):
        return self.__class__ == other.__class__ and self.command_cls == other.command_cls and self.editor == other.editor

    def repeat(self, minibuffer=None):
        """Shortcut to perform the same action again."""
        pass


class TextMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a text string
    """
    label = "Text"
    error = "Bad input."

    def create_primary_control(self, parent ,sizer):
        prompt = wx.StaticText(parent, -1, _(self.label))
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = wx.TextCtrl(parent, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 2)
        if self.help_text:
            c = wx.StaticText(parent, -1, self.help_text)
            c.SetToolTip(wx.ToolTip(self.help_tip))
            sizer.Add(c, 0, wx.ALIGN_CENTER_VERTICAL)
        self.text.Bind(wx.EVT_TEXT, self.on_text)
        self.text.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    # def set_best_size(self):
    #     self.text.SetMinSize((-1, 28))
    #     self.control.SetMinSize((-1, 28))

    def post_create(self):
         if self.initial:
            self.text.ChangeValue(self.initial)
            self.text.SetInsertionPointEnd()
            self.text.SetSelection(0, self.text.GetLastPosition())

    def focus(self):
        """
        Set the focus to the component in the menubar that should get
        the text focus.
        """
        log.debug("TextCtrl focus!!!")
        s1, s2 = self.text.GetSelection()
        self.text.SetFocus()
        self.text.SetSelection(s1, s2)

    def on_text(self, evt):
        text = evt.GetString()
        log.debug("text: %s" % text)
        self.perform()
        evt.Skip()

    def on_key_down(self, evt):
        keycode = evt.GetKeyCode()
        log.debug("key down: %s" % keycode)
        if keycode == wx.WXK_RETURN:
            self.repeat()
        evt.Skip()

    def convert(self, text):
        return text

    def get_raw_value(self):
        """Hook for subclasses to be able to modify the text control's value
        before being processed by getResult
        """
        return self.text.GetValue()

    def get_result(self, show_error=True):
        text = self.get_raw_value()
        error = None
        log.debug("text=%s" % text)
        try:
            text = self.convert(text)
        except:
            error = self.error
            if show_error:
                self.mode.frame.SetStatusText(error)
            text = None
        return text, error

    def clear_selection(self):
        # When text is selected, the insertion point is set to start of
        # selection.  Want to set it to the end of selection so the user can
        # continue typing after deselected.
        p = self.text.GetInsertionPoint()
        s1, s2 = self.text.GetSelection()
        if s1 != s2:
            p = s2
        self.text.SetSelection(p, p)
        self.text.SetInsertionPoint(p)

    def perform(self):
        """Execute the command associatied with this minibuffer"""
        value, error = self.get_result()
        cmd = self.command_cls(value, error, **self.kwargs)
        self.editor.process_command(cmd)

    def repeat(self, minibuffer=None):
        """Shortcut to perform the same action again."""
        value, error = self.get_result()
        if minibuffer is not None:
            kwargs = minibuffer.kwargs
        else:
            kwargs = self.kwargs
        cmd = self.command_cls(value, error, True, **kwargs)
        self.editor.process_command(cmd)


class NextPrevTextMinibuffer(TextMinibuffer):
    def __init__(self, editor, command_cls, next_cls, prev_cls, next_match=False, prev_match=False, **kwargs):
        TextMinibuffer.__init__(self, editor, command_cls, **kwargs)
        self.next_cls = next_cls
        self.prev_cls = prev_cls
        self.start_caret_index = -1
        self.search_command = None
        self.next_match = next_match
        self.prev_match = prev_match
        self.segment = editor.segment

    def create_header_controls(self, parent, sizer):
        print("BEFORE", self.editor.last_search_settings['match_case'])
        btn = FlatBitmapToggleButton(parent, -1, 'match_case', self.editor.last_search_settings['match_case'], "Case sensitive match")
        btn.Bind(wx.EVT_BUTTON, self.on_case_toggle)
        sizer.Add(btn, 0, wx.LEFT|wx.RIGHT, 2)

        if True:  # FIXME: regex not implemented yet
            return

        btn = FlatBitmapToggleButton(parent, -1, 'match_regex', False, "Regular expressions")
        btn.Bind(wx.EVT_BUTTON, self.on_regex_toggle)
        sizer.Add(btn, 0, wx.LEFT|wx.RIGHT, 2)

    def create_footer_controls(self, parent, sizer):
        btn = wx.Button(parent, -1, "Find Next")
        btn.Bind(wx.EVT_BUTTON, self.on_find_next)
        sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL)

        btn = wx.Button(parent, -1, "Find Prev")
        btn.Bind(wx.EVT_BUTTON, self.on_find_prev)
        sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL)

    def post_create(self):
        if self.initial:
            self.perform()
            # If using a previous search, select all text in case user wants to
            # start over again
            self.text.SetInsertionPointEnd()
            self.text.SetSelection(0, self.text.GetLastPosition())

    def change_editor(self, editor):
        self.segment.clear_style_bits(match=True)
        self.editor = editor
        self.segment = editor.segment
        self.search_command = None

    def is_repeat(self, other):
        return self.__class__ == other.__class__ and self.command_cls == other.command_cls and self.editor == other.editor and self.segment == other.segment and self.search_command is not None

    def on_key_down(self, evt):
        keycode = evt.GetKeyCode()
        mods = evt.GetModifiers()
        log.debug("key down: %s" % keycode)
        if keycode == wx.WXK_RETURN:
            if mods == wx.MOD_RAW_CONTROL or mods == wx.MOD_SHIFT:
                self.prev()
            else:
                next(self)
        evt.Skip()

    def __next__(self):
        if self.search_command is not None:
            cmd = self.next_cls(self.search_command)
            self.editor.process_command(cmd)
            self.clear_selection()

    def on_find_next(self, evt):
        next(self)
        evt.Skip()

    def prev(self):
        if self.search_command is not None:
            cmd = self.prev_cls(self.search_command)
            self.editor.process_command(cmd)
            self.clear_selection()

    def on_find_prev(self, evt):
        self.prev()
        evt.Skip()

    def on_case_toggle(self, evt):
        state = evt.IsChecked()
        log.debug("case: %s" % state)
        self.editor.last_search_settings['match_case'] = state
        log.debug("case toggle: current search settings: %s" % str(self.editor.last_search_settings))
        self.perform()
        evt.Skip()

    def on_regex_toggle(self, evt):
        state = evt.IsChecked()
        log.debug("regex: %s" % state)
        self.editor.last_search_settings['regex'] = state
        log.debug("regex toggle: current search settings: %s" % str(self.editor.last_search_settings))
        self.perform()
        evt.Skip()

    def perform(self):
        """Execute the command associatied with this minibuffer"""
        value, error = self.get_result()
        if self.start_caret_index < 0:
            self.start_caret_index = self.editor.search_start
        cmd = self.command_cls(self.start_caret_index, value, error, **self.kwargs)
        self.editor.process_command(cmd)
        self.search_command = cmd
        self.editor.last_search_settings["find"] = value
        log.debug("current search settings: %s" % str(self.editor.last_search_settings))
        self.clear_selection()

    def repeat(self, minibuffer=None):
        if minibuffer is not None:
            if minibuffer.next_match:
                next(self)
            elif minibuffer.prev_match:
                self.prev()
            else:
                self.text.SetFocus()
                self.text.SelectAll()


class IntMinibuffer(TextMinibuffer):
    """Dedicated subclass of Minibuffer that prompts for an integer.
    
    Can handle python expressions, with the enhancement that it recognizez
    hex numbers in the msw format of abcd1234h; i.e.  with a 'h' after the
    hex digits.
    """
    label = "Integer"
    error = "Not an integer expression."

    # Regular expression that matches MSW hex format
    msw_hex = re.compile("[0-9a-fA-F]+h")

    def convert(self, text):
        # replace each occurrence of a MSW-style hex number to 0x style so that
        # eval can parse it.
        text = self.msw_hex.sub(lambda s: "0x%s" % s.group(0)[:-1], text)
        number = int(eval(text))
        log.debug("number=%s" % number)
        return number


class IntRangeMinibuffer(IntMinibuffer):
    """Dedicated subclass of Minibuffer that prompts for a pair of integers.
    
    Can handle python expressions, with the enhancement that it recognizez
    hex numbers in the msw format of abcd1234h; i.e.  with a 'h' after the
    hex digits.
    """
    label = "Range"
    error = "Invalid range."

    def convert(self, text):
        # replace each occurrence of a MSW-style hex number to 0x style so that
        # eval can parse it.
        pair = []
        for val in text.split(','):
            pair.append(IntMinibuffer.convert(self, val))
        if len(pair) == 2:
            log.debug("range=%s" % str(pair))
            return pair
        raise ValueError("Didn't specify a range")


class FloatMinibuffer(TextMinibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a floating point
    number.
    """
    label = "Floating Point"
    error = "Not a numeric expression."

    def convert(self, text):
        number = float(eval(self.text.GetValue()))
        log.debug("number=%s" % number)
        return number


class InPlaceCompletionMinibuffer(TextMinibuffer):
    """Base class for a simple autocompletion minibuffer.

    This completion style is like Outlook's email address completion
    where it suggests the best completion ahead of the caret,
    adjusting as you type.  There is no dropdown list; everything is
    handled in the text ctrl.

    This class doesn't implement the complete method, leaving its
    implementation to subclasses.
    """

    def create_control(self, parent, **kwargs):
        self.control = wx.Panel(parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.control, -1, _(self.label))
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = wx.TextCtrl(self.control, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.control.SetSizer(sizer)

        self.text.Bind(wx.EVT_TEXT, self.OnText)
        self.text.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        if self.initial:
            self.text.ChangeValue(self.initial)

        self.control.saveSetFocus = self.control.SetFocus
        self.control.SetFocus = self.SetFocus

    def SetFocus(self):
        self.dprint(self)
        self.control.saveSetFocus()
        self.text.SetInsertionPointEnd()

    def OnText(self, evt):
        text = evt.GetString()
        self.dprint(text)
        evt.Skip()

    def complete(self, text):
        """Generate the completion list.

        The best guess should be returned as the first item in the
        list, with each subsequent entry being less probable.
        """
        raise NotImplementedError

    def processCompletion(self):
        text = self.text.GetValue()
        guesses = self.complete(text)
        if guesses:
            self.text.SetValue(guesses[0])
            self.text.SetSelection(len(text), -1)


class CompletionMinibuffer(TextMinibuffer):
    """Base class for a minibuffer based on the TextCtrlAutoComplete
    widget from the wxpython list.

    This class doesn't implement the complete method, leaving its
    implementation to subclasses.
    
    Most of the time completion minibuffers will want to extend the
    initial value when the use types something, but in case you want the
    initial buffer to be selected so that a keystroke replaces it, the
    'highlight_initial' kwarg can be passed to the constructor (which in turn
    passes it to create_control).
    """

    def create_control(self, parent, **kwargs):
        self.control = wx.Panel(parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.control, -1, _(self.label))
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = TextCtrlAutoComplete(self.control, choices=[], size=(-1,-1), style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.control.SetSizer(sizer)

        self.control.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

        if 'highlight_initial' in kwargs:
            self.highlight_initial = kwargs['highlight_initial']
        else:
            self.highlight_initial = False

        if self.initial is not None:
            self.text.ChangeValue(self.initial)
            self.text.SetChoices(self.complete(self.initial))
        self.text.SetEntryCallback(self.setDynamicChoices)
        #self.text.SetInsertionPointEnd()

        # FIXME: Using the EVT_SET_FOCUS doesn't seem to work to set the caret
        # to the end of the text.  It doesn't seem to get called at all, so
        # the only way to do it appears to be to co-opt the Panel's SetFocus
        # method
        self.control.saveSetFocus = self.control.SetFocus
        self.control.SetFocus = self.SetFocus

    def SetFocus(self):
        #dprint(self)
        self.control.saveSetFocus()
        self.OnFocus(None)

    def OnFocus(self, evt):
        #dprint()
        if self.highlight_initial and self.text.GetValue() == self.initial:
            self.text.SetSelection(-1, -1)
        else:
            self.text.SetInsertionPointEnd()

    def complete(self, text):
        raise NotImplementedError

    def setDynamicChoices(self):
        ctrl = self.text
        text = ctrl.GetValue()
        current_choices = ctrl.GetChoices()
        choices = self.complete(text)
        self.dprint(choices)
        if choices != current_choices:
            ctrl.SetChoices(choices)

    def getRawTextValue(self):
        """Get either the value from the dropdown list if it is selected, or the
        value from the text control.
        """
        self.text._setValueFromSelected()
        return self.text.GetValue()


class StaticListCompletionMinibuffer(CompletionMinibuffer):
    """Completion minibuffer where the list of possibilities doesn't change.

    This is used to complete on a static list of items.  This doesn't
    handle cases like searching through the filesystem where a new
    list of matches is generated when you hit a new directory.
    """

    allow_tab_complete_key_processing = True

    def __init__(self, *args, **kwargs):
        if 'list' in kwargs:
            self.sorted = kwargs['list']
        else:
            self.sorted = []
        CompletionMinibuffer.__init__(self, *args, **kwargs)

    def complete(self, text):
        """Return the list of completions that start with the given text"""
        found = []
        for match in self.sorted:
            if match.find(text) >= 0:
                found.append(match)
        return found


class LocalFileMinibuffer(CompletionMinibuffer):
    allow_tab_complete_key_processing = True

    def setDynamicChoices(self):
        text = self.text.GetValue()

        # NOTE: checking for ~ here rather than in OnKeyDown, because
        # OnKeyDown uses keyboard codes instead of strings.  On most
        # keyboards "~" is a shifted value and doesn't show up in the
        # keycodes.  You actually have to check for ord("`") and the
        # shift key, but that's under the assumption that the user
        # hasn't rearranged the keyboard
        if text[:-1] == self.initial:
            if text.endswith('~'):
                self.text.ChangeValue('~')
                self.text.SetInsertionPointEnd()
            elif text.endswith('/') or text.endswith(os.sep):
                self.text.ChangeValue(os.sep)
                self.text.SetInsertionPointEnd()
        elif wx.Platform == "__WXMSW__" and text[:-2] == self.initial:
            if text.endswith(':') and text[-2].isalpha():
                self.text.ChangeValue(text[-2:] + os.sep)
                self.text.SetInsertionPointEnd()
        CompletionMinibuffer.setDynamicChoices(self)

    def complete(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            prefix = wx.StandardPaths.Get().GetDocumentsDir()
            replace = len(prefix) + 1
            text = os.path.join(prefix, text[2:])
        else:
            replace = 0
        # FIXME: need to make this general by putting it in URLInfo
        paths = []
        try:
            # First, try to process the string as a unicode value.  This will
            # work in most cases on Windows and on unix when the locale is
            # set properly.  It returns unicode values
            globs = glob.glob(str(text)+"*")
            utf8 = False
        except UnicodeEncodeError:
            # When text is a unicode string but glob.glob is incapable of
            # processing unicode (usually only unix systems in the C/POSIX
            # locale).  It returns plain strings that will be converted using
            # utf-8
            globs = glob.glob(("%s*" % text).encode('utf-8'))
            utf8 = True
        except UnicodeDecodeError:
            # When the text is a utf-8 encoded string, but glob.glob can't
            # handle unicode (again, usually only unix systems in the C/POSIX
            # locale).  It also returns plain strings that need utf-8 decoding
            globs = glob.glob(text.encode('utf-8') + "*")
            utf8 = True
        for path in globs:
            if os.path.isdir(path):
                path += os.sep
            #dprint(path)
            if replace > 0:
                path = "~" + os.sep + path[replace:]

            # Always return unicode, so convert if necessary
            if utf8:
                paths.append(path.decode('utf-8'))
            else:
                paths.append(path)
        paths.sort()
        return paths

    def convert(self, text):
        if text.startswith("~/") or text.startswith("~\\"):
            text = os.path.join(wx.StandardPaths.Get().GetDocumentsDir(),
                                text[2:])
        return text


class TimelineMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that shows a timeline (ZoomRuler) control
    """
    label = "Timeline"
    error = "Bad input."
    show_close_button = False

    def create_primary_control(self, parent ,sizer):
        self.timeline = ZoomRuler(parent)
        sizer.Add(self.timeline, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 2)

    def post_create(self):
         if self.initial:
            pass

    def change_editor(self, editor):
        self.editor = editor
        self.timeline.rebuild(self.editor)
