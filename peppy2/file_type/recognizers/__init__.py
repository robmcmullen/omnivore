# All built-in recognizer plugins should be listed in this file so that the
# application can import this single file and determine the default plugins.
# It would be possible to scan the directory and import that way, but that
# leads to issues at py2exe time. I may readdress that at some point.

from image import ImageRecognizerPlugin

