""" Download manager using background threads
"""
import os
import time
import urllib.request, urllib.error, urllib.parse
import ssl
import tempfile

import wx
import wx.lib.scrolledpanel as scrolled

from ..utils.background_http import BaseRequest, BackgroundHttpMultiDownloader

import logging
log = logging.getLogger(__name__)


class NoCallback(object):
    def __call__(self):
        def no_callback(req):
            print(("no callback for", req))
            return
        return no_callback


class DownloadURLRequest(BaseRequest):
    blocksize = 64 * 1024

    debug = False

    def __init__(self, url, path, threadsafe_progress_callback=None, finished_callback=None):
        BaseRequest.__init__(self)
        self.url = url
        self.is_skippable = False
        self.expected_size = 0
        self.size = 0
        self.wants_cancel = False
        self.is_cancelled = False
        self.path = path
        self._threadsafe_progress_callback = None
        self._finished_callback = None
        self.threadsafe_progress_callback = threadsafe_progress_callback
        self.finished_callback = finished_callback

    @property
    def threadsafe_progress_callback(self):
        return self._threadsafe_progress_callback

    @threadsafe_progress_callback.setter
    def threadsafe_progress_callback(self, callback):
        if callback is not None:
            self._threadsafe_progress_callback = callback
        else:
            self._threadsafe_progress_callback = NoCallback()()

    @property
    def finished_callback(self):
        return self._finished_callback

    @finished_callback.setter
    def finished_callback(self, callback):
        if callback is not None:
            self._finished_callback = callback
        else:
            self._finished_callback = NoCallback()()

    def __str__(self):
        if not self.is_started:
            return "%s download pending" % (self.url)
        elif self.is_finished:
            if self.error is None:
                if self.data:
                    return "%d bytes in %s" % (self.size, self.path)
                elif self.is_cancelled:
                    return "%s cancelled, %d of %d bytes" % (self.url, self.size, self.expected_size)
                else:
                    return "%s incomplete download, %d of %d bytes" % (self.url, self.size, self.expected_size)
            else:
                return "%s error: %s" % (self.url, self.error)
        else:
            return "%s downloading, %d/%d" % (self.url, self.size, self.expected_size)

    def cancel(self):
        self.wants_cancel = True

    def get_data_from_server(self):
        try:
            request = urllib.request.Request(self.url)
            context = ssl._create_unverified_context()
            response = urllib.request.urlopen(request, context=context)
            headers = response.info()
            if "Content-Length" in headers:
                self.expected_size = int(headers['Content-Length'])
            finished = False
            tmp_path = self.path + ".download"
            with open(tmp_path, 'wb') as fh:
                while True:
                    chunk = response.read(self.blocksize)
                    if not chunk:
                        finished = True
                        break
                    if self.wants_cancel:
                        self.is_cancelled = True
                        break
                    fh.write(chunk)
                    self.size += len(chunk)
                    self.threadsafe_progress_callback(self)
                    if self.debug:
                        time.sleep(.1)
            if finished:
                try:
                    os.remove(self.path)
                except OSError:
                    pass
                os.rename(tmp_path, self.path)
                self.data = self.path
            self.finish()

        except (urllib.error.URLError, ValueError, OSError) as e:
            self.handle_error(e)

    def handle_error(self, e):
        self.error = e
        self.finish()

    def finish(self):
        self.is_finished = True
        self.threadsafe_progress_callback(self)
        self.threadsafe_progress_callback = None
        wx.CallAfter(self.finished_callback, self, self.error)
        self.finished_callback = None

    def get_gauge_value(self):
        if self.expected_size == 0:
            return -1
        return self.size * 100 / self.expected_size


class RequestStatusControl(wx.Panel):
    border = 5

    def __init__(self, parent, req, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.req = req
        hbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(hbox)
        self.text = wx.StaticText(self, -1, req.url, style=wx.ST_ELLIPSIZE_START)
        hbox.Add(self.text, 0, flag=wx.EXPAND|wx.ALL, border=self.border)
        vbox = wx.BoxSizer(wx.HORIZONTAL)
        self.gauge = wx.Gauge(self, -1)
        self.gauge.SetRange(100)
        vbox.Add(self.gauge, 1, flag=wx.EXPAND|wx.ALL)
        self.cancel = wx.Button(self, -1, "Cancel")
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        vbox.Add(self.cancel, 0, flag=wx.EXPAND|wx.LEFT, border=self.border)
        hbox.Add(vbox, 0, flag=wx.EXPAND|wx.ALL, border=self.border)
        hbox.Fit(self)
        self.Layout()

    def on_cancel(self, evt):
        self.req.cancel()

    def update(self):
        self.text.SetLabel(str(self.req))
        perc = self.req.get_gauge_value()
        if perc == -1:
            self.gauge.Pulse()
        else:
            self.gauge.SetValue(perc)
        if self.req.is_finished:
            self.cancel.Enable(False)


class DownloadControl(scrolled.ScrolledPanel):
    """
    View of list of downloaded items
    """

    def __init__(self, parent, downloader, path=None, prefix="downloads_", **kwargs):
        scrolled.ScrolledPanel.__init__(self, parent, -1, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.SetupScrolling(scroll_x=False)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.header = wx.StaticText(self, -1, "")
        hbox.Add(self.header, 1, flag=wx.ALIGN_CENTER)

        # Adding the button prevents the window from being dismissed when in a
        # sidebar popup, so need to use the lose_focus_helper
        self.lose_focus_helper_function = None

        self.setdir = wx.Button(self, -1, "Download Dir")
        self.setdir.Bind(wx.EVT_BUTTON, self.on_setdir)
        self.setdir.Bind(wx.EVT_KILL_FOCUS, self.on_lose_child_focus)  # helper!
        hbox.Add(self.setdir, 0, flag=wx.EXPAND|wx.ALL)
        sizer.Add(hbox, 0, flag=wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Layout()
        self.Fit()

        self.default_path = path
        self.dir_prefix = prefix
        self.downloader = downloader
        self.req_map = {}
        self.update_header()

    @property
    def path(self):
        if self.default_path:
            return default_path
        return tempfile.mkdtemp(prefix=self.dir_prefix)

    @path.setter
    def path(self, value):
        if value:
            self.default_path = value

    @property
    def num_active(self):
        count = 0
        for req in list(self.req_map.keys()):
            if not req.is_finished:
                count += 1
        return count

    def update_header(self):
        count = self.num_active
        if count == 0:
            text = "No active downloads"
        elif count == 1:
            text = "1 active download"
        else:
            text = "1 active download, %d queued" % (count - 1)
        self.header.SetLabel(text)

    def request_download(self, url, filename, callback):
        if not os.path.isabs(filename):
            filename = os.path.normpath(os.path.join(self.path, filename))
        log.debug("request_download: %s" % filename)
        req = DownloadURLRequest(url, filename, finished_callback=callback)
        self.add_request(req)
        return req

    def add_request(self, req):
        rc = RequestStatusControl(self, req)
        req.threadsafe_progress_callback = self.threadsafe_progress_callback
        self.req_map[req] = rc
        sizer = self.GetSizer()
        sizer.Add(rc, 0, flag=wx.EXPAND)
        self.Layout()
        self.SetupScrolling()
        self.downloader.send_request(req)
        rc.cancel.Bind(wx.EVT_KILL_FOCUS, self.on_lose_child_focus)

    def threadsafe_progress_callback(self, req):
        rc = self.req_map[req]
        wx.CallAfter(rc.update)
        wx.CallAfter(self.update_header)

    def on_setdir(self, evt):
        dlg = wx.DirDialog(self, "Choose the download directory:", style=wx.DD_DEFAULT_STYLE)
        dlg.SetPath(self.path)
        if dlg.ShowModal() == wx.ID_OK:
            self.path = dlg.GetPath()
        dlg.Destroy()

    def on_lose_child_focus(self, evt):
        log.debug("on_lose_child_focus! currently focused: %s next focused: %s" % (self.FindFocus(), evt.GetWindow()))
        evt.Skip()
        if self.lose_focus_helper_function is not None:
            self.lose_focus_helper_function(evt)


if __name__ == "__main__":
    # Due to the package import in the parent directory, running from this
    # directory won't work. Have to hack it:
    #
    # PYTHONPATH=../../.. python download_manager.py
    from ..background_http import BackgroundHttpDownloader
    import wx.lib.inspection

    class MyFrame(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.DefaultSize)
            self.dlcontrol = DownloadControl(self, None)

    class MyApp(wx.App):
        def OnInit(self):
            self.dlframe = MyFrame(None, -1, 'Download Manager')
            self.dlframe.Show(True)
            self.dlframe.Centre()
            return True

    def finished_callback(req, error):
        print(("FINISHED!", req))

    def do_download(dlc):
        req = dlc.request_download('http://playermissile.com', "index.html", finished_callback)
        req2 = dlc.request_download('http://playermissile.com/mame', "mame-index.html", finished_callback)
        req3 = dlc.request_download('http://playermissile.com/jumpman', "jumpman-index.html", finished_callback)
        req4 = dlc.request_download('http://playermissile.com/jumpman', "jumpman-index.html", finished_callback)
        req5 = dlc.request_download('http://playermissile.com/jumpman', "jumpman-index.html", finished_callback)

    app = MyApp(0)
    downloader = BackgroundHttpDownloader()
    app.dlframe.dlcontrol.downloader = downloader
    dlc = app.dlframe.dlcontrol
    DownloadURLRequest.blocksize = 1024
    wx.CallAfter(do_download, dlc)
    inspect = wx.lib.inspection.InspectionTool()
    wx.CallAfter(inspect.Show)

    app.MainLoop()

    downloader = None
