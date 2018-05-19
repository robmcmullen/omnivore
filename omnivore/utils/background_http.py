""" Threaded URL loading from

http://stackoverflow.com/questions/3817505/wxpython-htmlwindow-freezes-when-loading-images
"""

import urllib.request
import urllib.error
import os
import time
import threading
import queue

import logging
log = logging.getLogger(__name__)


class BaseRequest(object):
    def __init__(self):
        self.url = "no url"
        self.data = None
        self.error = None
        self.is_started = False
        self.is_finished = False
        self.is_skippable = True

    def __str__(self):
        if self.data is None:
            if self.error is None:
                return str(self.url)
            else:
                return "%s returned error: %s" % (self.url, self.error)
        else:
            return "%s returned %d bytes" % (self.url, len(self.data))

    def has_error(self):
        return self.error is not None

    def get_data_using_thread(self):
        self.is_started = True
        self.get_data_from_server()
        self.is_finished = True

    def get_data_from_server(self):
        self.data = "testing..."


class UnskippableRequest(BaseRequest):
    def __init__(self):
        BaseRequest.__init__(self)
        self.is_skippable = False


class URLRequest(BaseRequest):
    def __init__(self, url):
        BaseRequest.__init__(self)
        self.url = url

    def get_data_from_server(self):
        try:
            request = urllib.request.Request(self.url)
            response = urllib.request.urlopen(request)
            self.data = response.read()
        except urllib.error.URLError as e:
            self.error = e


class UnskippableURLRequest(URLRequest):
    def __init__(self, url):
        URLRequest.__init__(self, url)
        self.is_skippable = False


class HttpThread(threading.Thread):
    http_thread_count = 0

    def __init__(self, in_q, out_q, name_prefix="HttpThread"):
        self.__class__.http_thread_count += 1
        threading.Thread.__init__(self, name="%s-%d" % (name_prefix, self.http_thread_count))
        self.in_q = in_q
        self.out_q = out_q

    def get_next(self):
        req = self.in_q.get(True) # blocking
        return req

    def run(self):
        log.debug("%s: starting http thread..." % self.name)
        while True:
            log.debug("%s: waiting for request..." % self.name)
            req = self.get_next()
            if req is None:
                break

            log.debug("%s: loading from %s" % (self.name, req))
            req.get_data_using_thread()
            log.debug("%s: result from %s" % (self.name, req))
            self.out_q.put(req)


class OnlyLatestHttpThread(HttpThread):
    def get_next(self):
        """Return only the latest URL, skip any older ones as being outdated
        
        """
        req = BaseRequest()  # can't use None because None means quit
        wait = True
        while req is not None and req.is_skippable:
            log.debug("skipping req %s, skippable=%s", req, req.is_skippable)
            try:
                req = self.in_q.get(wait)
                log.debug("found req %s", req)
            except queue.Empty:
                break
            wait = False
        return req


class BackgroundHttpDownloader(object):
    def __init__(self):
        self.requests = queue.Queue()
        self.results = queue.Queue()
        self.thread = OnlyLatestHttpThread(self.requests, self.results, "BackgroundHttpDownloader")
        self.thread.start()
        log.debug("Created thread %s" % self.thread.name)
        self.get_server_config()

    def __del__(self):
        self.stop_threads()

    def stop_threads(self):
        self.requests.put(None)
        self.thread.join()
        log.debug("Stopped BackgroundHttpDownloader thread")

    def get_server_config(self):
        pass

    def send_request(self, req):
        self.requests.put(req)

    def get_finished(self):
        finished = []
        try:
            while True:
                data = self.results.get(False)
                finished.append(data)
        except queue.Empty:
            pass
        return finished


class BackgroundHttpMultiDownloader(object):
    def __init__(self, num_workers=4):
        self.requests = queue.Queue()
        self.results = queue.Queue()
        self.threads = []
        for i in range(num_workers):
            thread = HttpThread(self.requests, self.results, "BackgroundHttpMultiDownloader")
            thread.start()
            log.debug("Created thread %s" % thread.name)
            self.threads.append(thread)
        self.get_server_config()

    def __del__(self):
        self.stop_threads()

    def stop_threads(self):
        for t in self.threads:
            self.requests.put(None)
        for t in self.threads:
            t.join()

    def get_server_config(self):
        pass

    def send_request(self, req):
        self.requests.put(req)

    def get_finished(self):
        finished = []
        try:
            while True:
                data = self.results.get(False)
                finished.append(data)
        except queue.Empty:
            pass
        return finished


if __name__ == "__main__":

    downloader = BackgroundHttpDownloader()
    downloader.send_request(URLRequest('http://www.python.org/'))
    downloader.send_request(URLRequest('http://www.doughellmann.com/PyMOTW/contents.html'))
    downloader.send_request(URLRequest('http://playermissile.com'))
    downloader.send_request(URLRequest('http://docs.python.org/release/2.6.8/_static/py.png'))
    downloader.send_request(URLRequest('http://image.tmdb.org/t/p/w342/vpk4hLyiuI2SqCss0T3jeoYcL8E.jpg'))
    downloader.send_request(URLRequest('hvvttp://playermissile.com'))
    first = True
    for i in range(10):
        print(("STEP", i))
        downloaded = downloader.get_finished()
        for url in downloaded:
            print(('FINISHED:', url))
        if i > 1 and first:
            downloader.send_request(URLRequest('http://www.python.org/images/python-logo.gif'))
            downloader.send_request(URLRequest('http://www.python.org/'))
            downloader.send_request(URLRequest('http://www.doughellmann.com/PyMOTW/contents.html'))
            downloader.send_request(URLRequest('http://playermissile.com'))
            first = False
        time.sleep(1)

    downloader = None
