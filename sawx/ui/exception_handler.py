# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
# Copyright (c) 2008 Cody Precord <staff@editra.org>
# License: wxWindows License
import os, sys, platform, traceback, time, codecs, locale

import wx
import wx.stc


# dummy i18n handler
def _(text):
    return text


def FormatErrorMessage(app, err):
    """Returns a string of the systems information
    @return: System information string

    """
    info = list()
    info.append("#---- System Information ----#")
    info.append("%s Version: %s" % (app.app_name, app.app_version))
    info.append("Operating System: %s" % wx.GetOsDescription())
    if sys.platform == 'darwin':
        info.append("Mac OSX: %s" % platform.mac_ver()[0])
    info.append("Python Version: %s" % sys.version)
    info.append("wxPython Version: %s" % wx.version())
    info.append("wxPython Info: (%s)" % ", ".join(wx.PlatformInfo))
    info.append("Python Encoding: Default=%s  File=%s" % \
                (sys.getdefaultencoding(), sys.getfilesystemencoding()))
    info.append("System Architecture: %s %s" % (platform.architecture()[0], \
                                                platform.machine()))
    info.append("Byte order: %s" % sys.byteorder)
    info.append("Frozen: %s" % str(getattr(sys, 'frozen', 'False')))
    info.append("#---- End System Information ----#")
    info.extend(["", ""])
    info.append("#---- Traceback Info ----#")
    info.append(err)
    info.append("#---- End Traceback Info ----#")
    info.extend(["", ""])
    info.append("#---- Notes ----#")
    info.append("Please provide additional information about the crash here:")
    info.append("")
    return os.linesep.join(info)


def ExceptionHook(exctype, value, trace):
    """Handler for all unhandled exceptions
    @param exctype: Exception Type
    @param value: Error Value
    @param trace: Trace back info

    """
    ftrace = FormatTrace(exctype, value, trace)

    if ErrorDialog.ignore(ftrace):
        print(("Ignoring %s: %s" % (exctype, value)))
        return

    # Ensure that error gets raised to console as well
    print(ftrace)

    # If abort has been set and we get here again do a more forcefull shutdown
    if ErrorDialog.ABORT:
        os._exit(1)

    wx.CallAfter(ShowErrorDialog, ftrace)

def ShowErrorDialog(ftrace):
    # Make sure the user gets control of the mouse if it has been captured
    capture = wx.Window.GetCapture()
    if capture:
        capture.ReleaseMouse()

    # Prevent multiple reporter dialogs from opening at once
    if not ErrorDialog.REPORTER_ACTIVE and not ErrorDialog.ABORT:
        ErrorDialog(ftrace)


def FormatTrace(etype, value, trace):
    """Formats the given traceback
    @return: Formatted string of traceback with attached timestamp

    """
    exc = traceback.format_exception(etype, value, trace)
    return "".join(exc)


def TimeStamp():
    """Create a formatted time stamp of current time
    @return: Time stamp of the current time (Day Month Date HH:MM:SS Year)
    @rtype: string

    """
    now = time.localtime(time.time())
    now = time.asctime(now)
    return now


def send_email_via_gmail(subject, message, sender, passwd, recipient):
    import smtplib

    # Import the email modules we'll need
    from email.mime.text import MIMEText

    responses = []
    sent = False
    try:
        # Open a plain text file for reading.  For this example, assume that
        # the text file contains only ASCII characters.
        #fp = open(textfile, 'rb')
        # Create a text/plain message
        msg = MIMEText(message)
        # fp.close()

        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        s = smtplib.SMTP('smtp.gmail.com', 587)
        responses.append(s.starttls())
        responses.append(s.login(sender, passwd))
        responses.append(s.sendmail(msg['From'], [msg['To']], msg.as_string()))
        responses.append(s.quit())
        sent = True
    except Exception as e:
        wx.MessageBox("Unable to send email:\n\%s\n\nPlease email the bug report to %s" % (str(e), recipient))
        responses.append(e)
    text = "\n".join([str(r) for r in responses])
    return sent, text


def message_body_encode(body):
    import urllib.request, urllib.parse, urllib.error
    return urllib.parse.quote_plus(body).encode("utf-8")


def send_email_via_webbrowser(subject, message, recipient):
    import webbrowser

    sent = False
    error = ""
    try:
        msg = message_body_encode(message)
        url = 'mailto:%s?subject=%s&body=%s' % (recipient, subject, msg)

        webbrowser.open(url)
        sent = True
    except Exception as e:
        wx.MessageBox("Unable to send email:\n\%s\n\nPlease email the bug report to %s" % (str(e), recipient))
        error = str(e)
    return sent, error


#-----------------------------------------------------------------------------#

class ErrorReporter(object):
    """Crash/Error Reporter Service
    @summary: Stores all errors caught during the current session.

    """
    instance = None
    _first = True

    def __init__(self):
        """Initialize the reporter
        @note: The ErrorReporter is a singleton.

        """
        # Ensure init only happens once
        if self._first:
            object.__init__(self)
            self._first = False
            self._sessionerr = list()
        else:
            pass

    def __new__(cls, *args, **kargs):
        """Maintain only a single instance of this object
        @return: instance of this class

        """
        if not cls.instance:
            cls.instance = object.__new__(cls, *args, **kargs)
        return cls.instance

    def AddMessage(self, msg):
        """Adds a message to the reporters list of session errors
        @param msg: The Error Message to save

        """
        if msg not in self._sessionerr:
            self._sessionerr.append(msg)

    def GetErrorStack(self):
        """Returns all the errors caught during this session
        @return: formatted log message of errors

        """
        return (os.linesep * 2).join(self._sessionerr)

    def GetLastError(self):
        """Gets the last error from the current session
        @return: Error Message String

        """
        if len(self._sessionerr):
            return self._sessionerr[-1]

#-----------------------------------------------------------------------------#


ID_SEND = wx.NewId()
ID_IGNORE = wx.NewId()


class ErrorDialog(wx.Dialog):
    """Dialog for showing errors and and notifying developers should the
    user choose so.

    """
    ABORT = False
    REPORTER_ACTIVE = False

    user_requested_ignore = {}

    @classmethod
    def ignore(cls, message):
        return message in cls.user_requested_ignore

    def __init__(self, message):
        """Initialize the dialog
        @param message: Error message to display

        """
        self.app = wx.GetApp()

        ErrorDialog.REPORTER_ACTIVE = True
        wx.Dialog.__init__(self, None, title=_("%s Error/Crash Reporter" % self.app.app_name), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        # Save message in case the user wants to ignore further occurrences
        self._message = message

        # Add timestamp and give message to ErrorReporter
        current_frame = self.app.active_frame
        if self.app.active_frame is not None:
            summary = current_frame.active_editor.editor_summary
        else:
            summary = "No active editor."
        message = "********** %s **********\nEditor summary:\n%s\n\n%s" % (TimeStamp(), summary, message)
        ErrorReporter().AddMessage(message)

        # Attributes
        self.err_msg = FormatErrorMessage(self.app, ErrorReporter().GetErrorStack())

        # Layout
        self.SetMinSize(wx.Size(450, 600))
        self._panel = ErrorPanel(self, self.err_msg)
        self._DoLayout()

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnButton)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Auto show at end of init
        self.CenterOnParent()
        self.ShowModal()

    def _DoLayout(self):
        """Layout the dialog and prepare it to be shown
        @note: Do not call this method in your code

        """
        msizer = wx.BoxSizer(wx.VERTICAL)
        msizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(msizer)
        self.SetInitialSize()

    def OnButton(self, evt):
        """Handles button events
        @param evt: event that called this handler
        @postcondition: Dialog is closed
        @postcondition: If Report Event then email program is opened

        """
        e_id = evt.GetId()
        if e_id == wx.ID_CLOSE:
            self.Close()
        elif e_id == ID_SEND:
            status, error =  send_email_via_webbrowser(
                "%s Error Report" % self.app.app_name,
                self.err_msg,
                self.app.app_error_email_to)
            if status:
                self.Close()
            else:
                self._panel.text.AppendText(error)
                btn = wx.FindWindowById(ID_SEND, self)
                btn.Enable(False)
        elif e_id == wx.ID_ABORT:
            ErrorDialog.ABORT = True
            # Try a nice shutdown first time through
            app = wx.GetApp()
            app.quit()

            # Try again if it doesn't work
            for tlw in wx.GetTopLevelWindows():
                tlw.Destroy()

            wx.CallLater(500, app.ExitMainLoop)
            self.Close()
        elif e_id == wx.ID_IGNORE:
            self.user_requested_ignore[self._message] = True
            self.Close()
        else:
            evt.Skip()

    def OnClose(self, evt):
        """Cleans up the dialog when it is closed
        @param evt: Event that called this handler

        """
        ErrorDialog.REPORTER_ACTIVE = False
        self.EndModal(1)
        self.Destroy()
        evt.Skip()

#-----------------------------------------------------------------------------#


class ErrorPanel(wx.Panel):
    """Error Reporter panel"""

    def __init__(self, parent, msg):
        """Create the panel
        @param parent: wx.Window
        @param msg: Error message to display

        """
        wx.Panel.__init__(self, parent)

        self.err_msg = msg

        self.__DoLayout()

    def __DoLayout(self):
        """Layout the control"""
        icon = wx.StaticBitmap(self,
                               bitmap=wx.ArtProvider.GetBitmap(wx.ART_ERROR))
        mainmsg = wx.StaticText(self,
                                label=_("Error: Something unexpected happened.  You can attempt to continue,\nabort the program, or send an error report."))
        t_lbl = wx.StaticText(self, label=_("Error Traceback:"))
        tctrl = wx.TextCtrl(self, value=self.err_msg, size=(700, -1),
                            style=wx.TE_MULTILINE)
        tctrl.SetInsertionPoint(len(self.err_msg))
        self.text = tctrl
        wx.CallAfter(tctrl.ShowPosition, len(self.err_msg))

        abort_b = wx.Button(self, wx.ID_ABORT, _("Abort"))
        abort_b.SetToolTip(_("Exit the application"))
        close_b = wx.Button(self, wx.ID_CLOSE, ("Attempt to Continue"))
        send_b = wx.Button(self, ID_SEND, _("... and Send Error Report"))
        send_b.SetToolTip(_("Attempt to continue after sending error report"))
        send_b.SetDefault()
        ignore_b = wx.Button(self, wx.ID_IGNORE, ("Ignore Reoccurrences"))

        # Layout
        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.AddMany([((5, 5), 0), (icon, 0, wx.ALIGN_CENTER_VERTICAL),
                         ((12, 5), 0), (mainmsg, 0), ((5, 5), 0)])

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.AddMany([((5, 5), 0), (tctrl, 1, wx.EXPAND), ((5, 5), 0)])

        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.AddMany([((5, 5), 0), (abort_b, 0), ((-1, -1), 1, wx.EXPAND),
                        (close_b, 0), ((5, 5), 0), (send_b, 0), ((5, 5), 0),
                        (ignore_b, 0), ((5, 5), 0)])

        vsizer.AddMany([((5, 5), 0),
                        (hsizer1, 0),
                        ((10, 10), 0),
                        (t_lbl, 0, wx.ALIGN_LEFT),
                        ((3, 3), 0),
                        (hsizer2, 1, wx.EXPAND),
                        ((8, 8), 0),
                        (bsizer, 0, wx.EXPAND),
                        ((8, 8), 0)])

        self.SetMinSize(wx.Size(-1, 400))
        self.SetSizer(vsizer)
        self.SetAutoLayout(True)


save_hook = sys.excepthook
sys.excepthook = ExceptionHook
