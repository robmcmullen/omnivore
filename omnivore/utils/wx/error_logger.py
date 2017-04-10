# Standard library imports.
import os
import logging

# Monkey patch logging to support extra stuff

import __builtin__
known_loggers = dict()
logging_frame = None

orig_get_logger = logging.getLogger

def monkey_patch_get_logger(name=""):
    global known_loggers

    if name is not None and name not in known_loggers:
        known_loggers[name] = -1  # initially unknown logging level
        #print "Adding logger", name

    return orig_get_logger(name)

logging.getLogger = monkey_patch_get_logger


def show_logging_frame():
    global logging_frame

    # Wait until this function is called to import other packages so we don't
    # cause any module-loading-order-dependent problems by importing these
    # before needed in the application
    import wx

    log = logging.getLogger(__name__)

    # Logging handler & frame based on code from:
    # http://stackoverflow.com/questions/2819791/

    class WindowLogHandler(logging.Handler):
        """
        A handler class which sends log strings to a wx object
        """

        def __init__(self, printer):
            """
            Initialize the handler
            @param wxDest: the destination object to post the event to 
            @type wxDest: wx.Window
            """
            logging.Handler.__init__(self)
            self.level = logging.DEBUG
            self.printer = printer

        def flush(self):
            """
            does nothing for this handler
            """

        def emit(self, record):
            """
            Emit a record.

            """
            msg = self.format(record)
            wx.CallAfter(self.printer, msg + "\n")


    class LoggingFrame(wx.Frame):
        LEVELS = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]
        LEVEL_MAP = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL",
            }

        def __init__(self, parent, *args, **kwargs):
            wx.Frame.__init__(self, parent, *args, title="Debug Log Viewer", size=(800,600), **kwargs)
            panel = wx.Panel(self, wx.ID_ANY)
            self.text = wx.TextCtrl(panel, wx.ID_ANY, size=(800,600),
                              style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
            top_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            top_hsizer.Add(wx.StaticText(panel, -1, "Filter:"), 0, wx.ALL|wx.CENTER, 0)
            self.filter = wx.TextCtrl(panel, wx.ID_ANY)
            self.filter.Bind(wx.EVT_CHAR, self.on_char)
            top_hsizer.Add(self.filter, 1, wx.ALL|wx.CENTER, 0)
            bot_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            self.stats = wx.StaticText(panel, -1, "")
            bot_hsizer.Add(self.stats, 1, wx.ALL|wx.CENTER, 0)
            self.freeze = wx.Button(panel, wx.ID_ANY, 'Freeze')
            self.freeze.Bind(wx.EVT_BUTTON, self.on_freeze)
            bot_hsizer.Add(self.freeze, 0, wx.LEFT|wx.CENTER, 10)
            btn = wx.Button(panel, wx.ID_ANY, 'Show Logger State')
            btn.Bind(wx.EVT_BUTTON, self.on_known_button)
            bot_hsizer.Add(btn, 0, wx.LEFT|wx.CENTER, 10)
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.text, 1, wx.ALL|wx.EXPAND, 5)
            sizer.Add(top_hsizer, 0, wx.ALL|wx.EXPAND, 5)
            sizer.Add(bot_hsizer, 0, wx.ALL|wx.EXPAND, 5)
            panel.SetSizer(sizer)

            self.add_handler()
            self.get_default_levels()
            self.Bind(wx.EVT_CLOSE, self.on_close)
            self.is_frozen = False

        def on_close(self, evt):
            #self.remove_handler()
            self.Show(False)

        def Show(self, state=True):
            wx.Frame.Show(self, state)
            if state:
                self.filter.SetFocus()
                self.filter.SetInsertionPointEnd()
                self.text.SetInsertionPointEnd()

        def add_handler(self):
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            self.handler = WindowLogHandler(self.log)
            logger.addHandler(self.handler)
            self.handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(msg)s"))
            logger.setLevel(logging.INFO)

        def remove_handler(self):
            logger = logging.getLogger()
            logger.removeHandler(self.handler)

        def get_default_levels(self):
            loggers = known_loggers.copy()  # can't operate on dict when iterating
            for logger_name, level in loggers.iteritems():
                if level < 0:
                    known_log = logging.getLogger(logger_name)
                    level = known_log.getEffectiveLevel()
                    known_loggers[logger_name] = level
                    log.debug("default log level for %s: %s" % (logger_name, self.LEVEL_MAP.get(level, str(level))))

        def log(self, msg, override=False):
            if not self.is_frozen or override:
                if not msg.endswith("\n"):
                    msg += "\n"
                self.text.AppendText(msg)
                # self.text.SetInsertionPointEnd()

        def show_known(self):
            ruler = "----------------------------------------------------------"
            self.log("\n%s\nKNOWN LOGGER NAMES:\n" % ruler)
            for logger_name in sorted(known_loggers):
                log = logging.getLogger(logger_name)
                level = log.getEffectiveLevel()
                self.log("%s %s\n" % (self.LEVEL_MAP.get(level, str(level)), logger_name), override=True)
            self.log("%s\n\n" % ruler)

        def on_test_button(self, evt):
            import random
            log.log(random.choice(self.LEVELS), "More? click again!")

        def on_known_button(self, evt):
            self.show_known()

        def on_freeze(self, evt):
            if self.is_frozen:
                self.freeze.SetLabel(" Freeze ")
                self.is_frozen = False
            else:
                self.freeze.SetLabel("Resume")
                self.is_frozen = True

        def on_char(self, evt):
            evt.Skip()
            wx.CallAfter(self.process_value)

        def process_value(self):
            text = self.filter.GetValue()
            if not text:
                return
            match_strings = [t.strip() for t in text.split(",") if t] if "," in text else [text.strip()] if text else []
            count = 0
            for logger_name, level in known_loggers.iteritems():
                if level < 0:
                    level = logging.INFO
                for match in match_strings:
                    if match in logger_name:
                        level = logging.DEBUG
                        count += 1
                        break
                log = logging.getLogger(logger_name)
                log.setLevel(level)
            label = "1 debug logger enabled" if count == 1 else "%d debug loggers enabled" % count
            self.stats.SetLabel(label)

    if logging_frame is None:
        logging_frame = LoggingFrame(None)
        logging_frame.show_known()
    logging_frame.Show()


if __name__ == '__main__':
    import wx
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("omnivore")
    log = logging.getLogger("omnivore.framework")
    log = logging.getLogger("omnivore.framework.editor")
    log = logging.getLogger("omnivore8bit.hex_edit")
    log = logging.getLogger("omnivore.utils.wx.error_logger")
    app = wx.App(redirect = False)
    show_logging_frame()
    app.MainLoop()
