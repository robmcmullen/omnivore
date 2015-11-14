import os
import re

import wx

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
    
    def __init__(self, editor, command_cls, label=None, initial=None):
        self.control = None
        self.editor = editor
        self.command_cls = command_cls
        if label is not None:
            self.label = label
        else:
            self.label = command_cls.pretty_name
        self.initial = initial
        
    def create_control(self, parent, **kwargs):
        """
        Create a window that represents the minibuffer, and set
        self.control to that window.
        
        @param parent: parent window of minibuffer
        """
        panel = wx.Panel(parent, -1, name="Minibuffer")
        panel.SetSize((500, 40))
        panel.SetBackgroundColour('blue')
        self.control = panel

    def repeat(self, action):
        """Entry point used to reinitialize the minibuffer without creating
        a new instance.
        
        @param action: the L{SelectAction} that caused the repeat, which could
        be different than C{self.action} stored during the __init__ method.
        """
        raise NotImplementedError

    def focus(self):
        """
        Set the focus to the component in the menubar that should get
        the text focus.
        """
        log.debug("focus!!!")
        self.control.SetFocus()
    
    def destroy(self):
        """
        Destroy the minibuffer widgets.
        """
        self.panel.Destroy()
        self.panel = None
    
    def perform(self, value):
        """Execute the processMinibuffer method of the action"""
        cmd = self.command_cls(value)
        error = self.action.processMinibuffer(self, self.mode, value)
        if error is not None:
            self.mode.frame.SetStatusText(error)



class TextMinibuffer(Minibuffer):
    """
    Dedicated subclass of Minibuffer that prompts for a text string
    """
    label = "Text"
    error = "Bad input."
    
    def create_control(self, parent, **kwargs):
        self.control = wx.Panel(parent, style=wx.NO_BORDER|wx.TAB_TRAVERSAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        prompt = wx.StaticText(self.control, -1, _(self.label))
        sizer.Add(prompt, 0, wx.CENTER)
        self.text = wx.TextCtrl(self.control, -1, size=(-1,-1), style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.control.SetSizer(sizer)

        if self.initial:
            self.text.ChangeValue(self.initial)
            self.text.SetInsertionPointEnd() 
            self.text.SetSelection(0, self.text.GetLastPosition()) 
        
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
    where it suggests the best completion ahead of the cursor,
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

        # FIXME: Using the EVT_SET_FOCUS doesn't seem to work to set the cursor
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
            globs = glob.glob(unicode(text)+"*")
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
