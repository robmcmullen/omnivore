""" Threaded URL loading from

http://stackoverflow.com/questions/3817505/wxpython-htmlwindow-freezes-when-loading-images
"""

import urllib2 as urllib2
import os
import time
import threading
import multiprocessing
import Queue

import logging
log = multiprocessing.log_to_stderr()
log.setLevel(logging.DEBUG)


class BaseURLRequest(object):
    def __init__(self):
        self.url = "no url"
        self.data = None
        self.error = None
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
        self.get_data_from_server()
        self.is_finished = True
    
    def get_data_from_server(self):
        self.data = "testing..."


class URLRequest(BaseURLRequest):
    def __init__(self, url):
        BaseURLRequest.__init__(self)
        self.url = url

    def get_data_from_server(self):
        try:
            request = urllib2.Request(self.url)
            response = urllib2.urlopen(request)
            self.data = response.read()
        except urllib2.URLError, e:
            self.error = e


class UnskippableURLRequest(URLRequest):
    def __init__(self, url):
        URLRequest.__init__(self, url)
        self.is_skippable = False


class HttpThread(threading.Thread):
    def __init__(self, in_q, out_q):
        threading.Thread.__init__(self)
        self.in_q = in_q
        self.out_q = out_q

    def get_next(self):
        url = self.in_q.get(True) # blocking
        return url

    def run(self):
        log.debug("%s: starting http thread..." % self.name)
        while True:
            log.debug("%s: waiting for URL..." % self.name)
            url = self.get_next()
            if url is None:
                break
            
            log.debug("%s: loading from %s" % (self.name, url))
            url.get_data_using_thread()
            log.debug("%s: result from %s" % (self.name, url))
            self.out_q.put(url)
            


class OnlyLatestHttpThread(HttpThread):
    def get_next(self):
        """Return only the latest URL, skip any older ones as being outdated
        
        """
        url = BaseURLRequest()  # can't use None because None means quit
        wait = True
        while url is not None and url.is_skippable:
            try:
                url = self.in_q.get(wait)
                log.debug("found url %s", url)
            except Queue.Empty:
                break
            wait = False
        return url


class BackgroundHttpDownloader(object):
    def __init__(self):
        self.urlq = Queue.Queue()
        self.results = Queue.Queue()
        self.thread = OnlyLatestHttpThread(self.urlq, self.results)
        self.thread.start()
        self.get_server_config()
    
    def __del__(self):
        self.urlq.put(None)
        self.thread.join()
    
    def get_server_config(self):
        pass
    
    def send_request(self, url):
        self.urlq.put(url)
    
    def get_finished(self):
        finished = []
        try:
            while True:
                data = self.results.get(False)
                finished.append(data)
        except Queue.Empty:
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
        print "STEP", i
        downloaded = downloader.get_finished()
        for url in downloaded:
            print 'FINISHED:', url
        if i > 1 and first:
            downloader.send_request(URLRequest('http://www.python.org/images/python-logo.gif'))
            downloader.send_request(URLRequest('http://www.python.org/'))
            downloader.send_request(URLRequest('http://www.doughellmann.com/PyMOTW/contents.html'))
            downloader.send_request(URLRequest('http://playermissile.com'))
            first = False
        time.sleep(1)
            
    downloader = None
