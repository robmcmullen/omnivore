===============================
MIME Types and File Recognizers
===============================

General MIME references:

* http://www.iana.org/assignments/media-types/media-types.xhtml

Filename to MIME type
=====================

* python builtin:

  * import mimetypes
  * mimetypes.guess_type("file.pyc")
    ('application/x-python-code', None)
    
* On linux, /usr/share/mime contains a whole host of subdirs that map file extensions to mime types
* http://svn.apache.org/repos/asf/httpd/httpd/trunk/docs/conf/mime.types
* http://hul.harvard.edu/ois/systems/wax/wax-public-help/mimetypes.htm

Magic bytes and parsers
=======================

* http://www.darwinsys.com/file/

  * source: https://github.com/glensc/file
  
* A magic file parser (in perl, so I can't figure it out) http://cpansearch.perl.org/src/MICHIELB/File-MimeInfo-0.21/lib/File/MimeInfo/Magic.pm
* http://httpd.apache.org/docs/current/mod/mod_mime_magic.html

  * source: https://github.com/apache/httpd/blob/trunk/modules/metadata/mod_mime_magic.c
  
* A non-magic file signature list: http://www.garykessler.net/library/file_sigs.html
* python magic file parser: https://github.com/devttys0/binwalk/blob/master/src/binwalk/core/parser.py
* binary file editor: https://bitbucket.org/haypo/hachoir
