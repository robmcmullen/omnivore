# peppy Copyright (c) 2006-2010 Rob McMullen
# HTML conversion subroutines Copyright (c) 2010 Christopher Barker
# This file is licenced under the same terms as Python itself
"""Utility functions for operating on text

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.
"""
import re

import logging
log = logging.getLogger(__name__)

def piglatin(text):
    """Translate string to pig latin.
    
    Simple pig latin translator that properly capitalizes the resulting string,
    and skips over any leading or trailing non-alphabetic characters.
    """
    words = []
    for w in text.split():
        # Find non alphabetic chars at the start and skip them
        i=0
        while not w[i].isalpha():
            i += 1
        start = w[0:i]
        w = w[i:]
        
        if w[0] in 'aeiouAEIOU':
            prefix = w
            suffix = 'way'
        else:
            if w[0].isupper():
                prefix = w[1:].capitalize()
                suffix = w[0].lower() + 'ay'
            else:
                prefix = w[1:]
                suffix = w[0].lower() + 'ay'
        
        # Move any trailing non-alphabetic characters to the end
        i = len(prefix) - 1
        while i >= 0 and not prefix[i].isalpha():
            i -= 1
        end = prefix[i + 1:]
        prefix = prefix[0:i + 1]
        
        word = start + prefix + suffix + end
        #print "preprefix=%s, prefix=%s, suffix=%s, word=%s" % (preprefix, prefix, suffix, word)
        words.append(word)
    return u' '.join(words)

def getMagicComments(bytes, headersize=1024):
    """Given a byte string, get the first two lines.
    
    "Magic comments" appear in the first two lines of the file, and can
    indicate the encoding of the file or the major mode in which the file
    should be interpreted.
    """
    numbytes = len(bytes)
    if headersize > numbytes:
        headersize = numbytes
    header = bytes[0:headersize]
    lines = header.splitlines()
    return lines[0:2]

def detectBOM(bytes):
    """Search for unicode Byte Order Marks (BOM)
    """
    boms = {
        'utf-8': '\xef\xbb\xbf',
        'utf-16-le': '\xff\xfe',
        'utf-16-be': '\xfe\xff',
        'utf-32-le': '\xff\xfe\x00\x00',
        'utf-32-be': '\x00\x00\xfe\xff',
        }
    # FIXME: utf-32 is not available in python 2.5, only 2.6 and later.
    
    for encoding, bom in boms.iteritems():
        if bytes.startswith(bom):
            return encoding, bom
    return None, None

def detectEncoding(bytes):
    """Search for "magic comments" that specify the encoding
    
    @returns tuple containing (encoding name, BOM) where both may be None.  If
    the Byte Order Mark is not None, the bytes should be stripped off before
    decoding using the encoding name.
    """
    if isinstance(bytes, str):
        # Only check byte order marks when the input is a raw string.  If the
        # input is unicode, it can't have a valid byte order mark.
        encoding, bom = detectBOM(bytes)
        if encoding:
            return encoding, bom
    lines = getMagicComments(bytes)
    regex = re.compile("coding[:=]\s*([-\w.]+)")
    for txt in lines:
        match = regex.search(txt)
        if match:
            log.debug("guessEncoding: Found encoding %s" % match.group(1))
            return match.group(1), None
    return None, None

def encodedBytesToUnicode(bytes, encoding, bom):
    if bom:
        start = len(bom)
    else:
        start = 0
    unicodestring = bytes[start:].decode(encoding)
    return unicodestring

def parseEmacs(header):
    """Determine if the header specifies a major mode.
    
    Parse a potential emacs major mode specifier line into the
    mode and the optional variables.  The mode may appears as any
    of::

      -*-C++-*-
      -*- mode: Python; -*-
      -*- mode: Ksh; var1:value1; var3:value9; -*-

    @param header: first x bytes of the file to be loaded
    @return: two-tuple of the mode and a dict of the name/value pairs.
    @rtype: tuple
    """
    import emacsutil
    
    lines = getMagicComments(header)
    for line in lines:
        mode, vars = emacsutil.parseModeline(line)
        if mode:
            return mode, vars
    return None, None

def guessBinary(text, percentage=5):
    """Guess if this is a text or binary file.
    
    Guess if the text in this file is binary or text by scanning
    through the first C{amount} characters in the file and
    checking if some C{percentage} is out of the printable ascii
    range.

    Obviously this is a poor check for unicode files, so this is
    just a bit of a hack.

    @param amount: number of characters to check at the beginning
    of the file

    @type amount: int

    @param percentage: percentage of characters that must be in
    the printable ASCII range

    @type percentage: number

    @rtype: boolean
    """
    encoding, bom = detectEncoding(text)
    if encoding:
        # The presence of an encoding by definition indicates a text file, so
        # therefore not binary!
        return False
    data = [ord(i) for i in text]
    binary=0
    for ch in data:
        if (ch<8) or (ch>13 and ch<32) or (ch>126):
            binary+=1
    log.debug("guessBinary: len=%d, num binary=%d" % (len(text), binary))
    if binary>(len(text)/percentage):
        return True
    return False


def guessSpacesPerIndent(text):
    """Guess the number of spaces per indent level
    
    Takes from the SciTE source file SciTEBase::DiscoverIndentSetting
    """
    tabsizes = [0]*9
    indent = 0 # current line indentation
    previndent = 0 # previous line indentation
    prevsize = -1 # previous line tab size
    newline = True
    for c in text:
        if c == '\n' or c == '\r':
            newline = True
            indent = 0
        elif newline:
            if c == ' ':
                indent += 1
            else:
                if indent:
                    if indent == previndent and prevsize >= 0:
                        tabsizes[prevsize] += 1
                    elif indent > previndent and previndent >= 0:
                        if indent - previndent <= 8:
                            prevsize = indent - previndent
                            tabsizes[prevsize] += 1
                        else:
                            prevsize = -1
                    previndent = indent
                elif c == '\t':
                    tabsizes[0] += 1
                newline = False
    
    # find maximum non-zero indent
    index = -1
    for i, size in enumerate(tabsizes):
        if size > 0 and (index == -1 or size > tabsizes[index]):
            index = i
    
    return index

# HTML converters from Chris Barker:
#
# This is an alternative to using <pre> -- I want it to wrap, but otherwise
# preserve newlines, etc.  Perhaps is would make sense to use some of
# the stuff ion webhelpers, instead of writting this all from scratch:
# http://webhelpers.groovie.org/

def wrapFont(text, font_size=None):
    if font_size is not None:
        text = "<font size=%d>%s</font>" % (font_size, text)
    return text

def text2HtmlPlain(text, font_size=None):
    """
    Takes raw text, and returns html with newlines converted, etc.
    
    Used the default font, with no extra whitespace games.
    """
    # double returns are a new paragraph
    text = text.split("\n\n")
    text = [p.strip().replace("\n","<br>") for p in text]
    body = wrapFont("<p>\n" + "\n</p>\n<p>\n".join(text) + "\n</p>\n", font_size)
    text = "<html>\n<body>\n" + body + "</body>\n</html>"
    return text

def text2HtmlFixed(text, font_size=None):
    """
    Takes raw text, and returns html with newlines converted, etc., using a fixed width font.
    It should also preserve text lined up with spaces.
    """
    text = text.replace("\n","<br>")
    # this preserves multiple spaces: it does mess up breaking on a two space gap
    text = text.replace("  ","&nbsp;&nbsp;")
    body = wrapFont("<p>\n" + text + "\n</p>\n", font_size)
    text = "<html>\n<body>\n<tt>\n" + body + "</tt></body>\n</html>"
    return text

def text2HtmlParagraph(text, font_size=None):
    """
    Takes raw text, and returns html with consecutive non-blank lines
    converted to paragraphs.
    
    Used the default font, with no extra whitespace games.
    """
    # double returns are a new paragraph
    text = text.split("\n\n")
    text = [p.strip().replace("\n","") for p in text]
    body = wrapFont("<p>\n" + "\n</p>\n<p>\n".join(text) + "\n</p>\n", font_size)
    text = "<html>\n<body>\n" + body + "</body>\n</html>"
    return text


def text_to_int(text, default_base="dec"):
    """ Convert text to int, raising exeception on invalid input
    """
    if text.startswith("0x"):
        value = int(text[2:], 16)
    elif text.startswith("$"):
        value = int(text[1:], 16)
    elif text.startswith("#"):
        value = int(text[1:], 10)
    elif text.startswith("%"):
        value = int(text[1:], 2)
    else:
        if default_base == "dec":
            value = int(text)
        else:
            value = int(text, 16)
    return value


if __name__ == "__main__":
    import sys
    
    for file in sys.argv[1:]:
        fh = open(file)
        text = fh.read()
        log.debug("file=%s, tabsize=%d" % (file, guessSpacesPerIndent(text)))
