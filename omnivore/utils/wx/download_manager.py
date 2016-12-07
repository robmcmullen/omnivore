""" Download manager using background threads
"""
import os
import time
import urllib2

import wx
import wx.lib.scrolledpanel as scrolled

from omnivore.utils.background_http import BaseRequest, BackgroundHttpMultiDownloader

import logging
log = logging.getLogger(__name__)

class NoCallback(object):
    def __call__(self):
        def no_callback(req):
            print "no callback for", req
            return
        return no_callback

class DownloadURLRequest(BaseRequest):
    blocksize = 64 * 1024

    debug = False

    def __init__(self, url, path, threadsafe_progress_callback=None, threadsafe_finished_callback=None):
        BaseRequest.__init__(self)
        self.url = url
        self.is_skippable = False
        self.expected_size = 0
        self.size = 0
        self.wants_cancel = False
        self.is_cancelled = False
        self.path = path
        self._threadsafe_progress_callback = None
        self._threadsafe_finished_callback = None
        self.threadsafe_progress_callback = threadsafe_progress_callback
        self.threadsafe_finished_callback = threadsafe_finished_callback

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
    def threadsafe_finished_callback(self):
        return self._threadsafe_finished_callback
    
    @threadsafe_finished_callback.setter
    def threadsafe_finished_callback(self, callback):
        if callback is not None:
            self._threadsafe_finished_callback = callback
        else:
            self._threadsafe_finished_callback = NoCallback()()

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
            request = urllib2.Request(self.url)
            response = urllib2.urlopen(request)
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

        except (urllib2.URLError, ValueError, OSError), e:
            self.handle_error(e)

    def handle_error(self, e):
        self.error = e
        self.finish()

    def finish(self):
        self.is_finished = True
        self.threadsafe_progress_callback(self)
        self.threadsafe_progress_callback = None
        if self.error is None:
            self.threadsafe_finished_callback(self)
        self.threadsafe_finished_callback = None

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
        self.text = wx.StaticText(self, -1, req.url)
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

    def __init__(self, parent, downloader, **kwargs):
        scrolled.ScrolledPanel.__init__(self, parent, -1, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.SetupScrolling(scroll_x=False)
        self.SetSizer(sizer)
        sizer.Layout()
        self.Fit()
        self.downloader = downloader
        self.req_map = {}

    def add_request(self, req):
        rc = RequestStatusControl(self, req)
        req.threadsafe_progress_callback = self.threadsafe_progress_callback
        self.req_map[req] = rc
        sizer = self.GetSizer()
        sizer.Add(rc, 0, flag=wx.EXPAND)
        self.Layout()
        self.SetupScrolling()
        self.downloader.send_request(req)

    def threadsafe_progress_callback(self, req):
        rc = self.req_map[req]
        wx.CallAfter(rc.update)


if __name__ == "__main__":
    from omnivore.utils.background_http import BackgroundHttpDownloader
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

    def threadsafe_finished_callback(req):
        print "FINISHED!", req

    app = MyApp(0)
    downloader = BackgroundHttpDownloader()
    app.dlframe.dlcontrol.downloader = downloader
    DownloadURLRequest.blocksize = 1024
    req = DownloadURLRequest('http://playermissile.com', "index.html", threadsafe_finished_callback=threadsafe_finished_callback)
    wx.CallAfter(app.dlframe.dlcontrol.add_request, req)
    req2 = DownloadURLRequest('http://playermissile.com/mame', "mame-index.html", threadsafe_finished_callback=threadsafe_finished_callback)
    wx.CallAfter(app.dlframe.dlcontrol.add_request, req2)
    req3 = DownloadURLRequest('http://playermissile.com/jumpman', "jumpman-index.html", threadsafe_finished_callback=threadsafe_finished_callback)
    wx.CallAfter(app.dlframe.dlcontrol.add_request, req3)
    req4 = DownloadURLRequest('http://playermissile.com/jumpman', "jumpman-index.html", threadsafe_finished_callback=threadsafe_finished_callback)
    wx.CallAfter(app.dlframe.dlcontrol.add_request, req4)
    req5 = DownloadURLRequest('http://playermissile.com/jumpman', "jumpman-index.html", threadsafe_finished_callback=threadsafe_finished_callback)
    wx.CallAfter(app.dlframe.dlcontrol.add_request, req5)
    app.MainLoop()

    downloader = None
