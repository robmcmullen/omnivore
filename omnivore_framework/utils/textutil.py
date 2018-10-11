# peppy Copyright (c) 2006-2010 Rob McMullen
# HTML conversion subroutines Copyright (c) 2010 Christopher Barker
# This file is licenced under the same terms as Python itself
"""Utility functions for operating on text

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.
"""
import re
from collections import OrderedDict

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
    return ' '.join(words)


def getMagicComments(data, headersize=1024):
    """Given a byte string, get the first two lines.
    
    "Magic comments" appear in the first two lines of the file, and can
    indicate the encoding of the file or the major mode in which the file
    should be interpreted.
    """
    numbytes = len(data)
    if headersize > numbytes:
        headersize = numbytes
    header = data[0:headersize]
    lines = header.splitlines()
    return lines[0:2]


def detectBOM(data):
    """Search for unicode Byte Order Marks (BOM)
    """
    boms = {
        'utf-8': b'\xef\xbb\xbf',
        'utf-16-le': b'\xff\xfe',
        'utf-16-be': b'\xfe\xff',
        'utf-32-le': b'\xff\xfe\x00\x00',
        'utf-32-be': b'\x00\x00\xfe\xff',
        }
    # FIXME: utf-32 is not available in python 2.5, only 2.6 and later.

    for encoding, bom in list(boms.items()):
        if data.startswith(bom):
            return encoding, bom
    return None, None


def detectEncoding(data):
    """Search for "magic comments" that specify the encoding
    
    @returns tuple containing (encoding name, BOM) where both may be None.  If
    the Byte Order Mark is not None, the bytes should be stripped off before
    decoding using the encoding name.
    """
    if isinstance(data, str):
        # Only check byte order marks when the input is a bytes.  If the
        # input is unicode, it can't have a valid byte order mark.
        return unicode, None
    encoding, bom = detectBOM(data)
    if encoding:
        return encoding, bom
    lines = getMagicComments(data)
    regex = re.compile(b"coding[:=]\s*([-\w.]+)")
    for txt in lines:
        match = regex.search(txt)
        if match:
            log.debug("guessEncoding: Found encoding %s" % match.group(1))
            return match.group(1), None
    return None, None


def encodedBytesToUnicode(data, encoding, bom):
    if bom:
        start = len(bom)
    else:
        start = 0
    unicodestring = data[start:].decode(encoding)
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
    from . import emacsutil

    lines = getMagicComments(header)
    for line in lines:
        mode, vars = emacsutil.parseModeline(line)
        if mode:
            return mode, vars
    return None, None


def guessBinary(data, percentage=5):
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
    encoding, bom = detectEncoding(data)
    if encoding:
        # The presence of an encoding by definition indicates a text file, so
        # therefore not binary!
        return False
    binary=0
    for ch in data:
        if (ch<8) or (ch>13 and ch<32) or (ch>126):
            binary+=1
    log.debug("guessBinary: len=%d, num binary=%d" % (len(data), binary))
    if binary>(len(data)/percentage):
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


def parse_int_label_dict(text, base=10, allow_equals=False):
    """Parse a multi-line text string into a dict keyed on integers with a
    keyword value

    For each line, it tries to find the first integer-looking thing and use
    that as the key, and the first label-looking thing (alphanumeric, starting
    with a letter or _, and stopping at the first non-alphanumeric or
    whitespace) and use that as the label.

    If ``allow_equal`` is True, it will check for the presense of an ``=``
    character and parse in the reverse order, where the label comes first and
    the address follows after the equals character.
    """
    regex = re.compile("(0x|\$)?([0-9a-fA-F]+)[^a-zA-Z]+([a-zA-Z_]\w*)")
    regex_eq = re.compile("([a-zA-Z_]\w*)[^a-zA-Z=]*=.*?(0x|\$)?([0-9a-fA-F]+)")
    d = {}
    for line in text.splitlines():
        match = None
        if allow_equals and "=" in line:
            match = regex_eq.search(line)
            key = match.group(3)
            value = match.group(1)
            b = match.group(2)

        if not match:
            match = regex.search(line)

            if match:
                key = match.group(2)
                value = match.group(3)
                b = match.group(1)
        if match:
            line_base = 16 if b == "$" or b == "0x" else 10 if b == "#" else base
            try:
                key = int(key, line_base)
                d[key] = value
            except ValueError:
                # just ignore bad lines
                pass
    return d


def slugify(s):
    """Simplifies ugly strings into something URL-friendly.

    >>> print slugify("[Some] _ Article's Title--")
    some-articles-title

    From https://gist.github.com/dolph/3622892#file-slugify-py
    """

    # "[Some] _ Article's Title--"
    # "[some] _ article's title--"
    s = s.lower()

    # "[some] _ article's_title--"
    # "[some]___article's_title__"
    for c in [' ', '-', '.', '/']:
        s = s.replace(c, '_')

    # "[some]___article's_title__"
    # "some___articles_title__"
    s = re.sub('\W', '', s)

    # "some___articles_title__"
    # "some   articles title  "
    s = s.replace('_', ' ')

    # "some   articles title  "
    # "some articles title "
    s = re.sub('\s+', ' ', s)

    # "some articles title "
    # "some articles title"
    s = s.strip()

    # "some articles title"
    # "some-articles-title"
    s = s.replace(' ', '-')

    return s


def pretty_seconds(s, precision=1):
    """Convert a number of seconds into a single text string with a decimal
    number followed by the largest single unit of time that causes the result
    to be greater than one.
    """
    fmt = "%%.%df" % precision
    if s < 1:
        fmt = "%d"
        val = s * 1000.0
        ext = "ms"
    elif s < 60:
        val = s
        ext = "s"
    elif s < 3600:
        val = (s / 60.0)
        ext = "m"
    elif s < 86400:
        val = (s / 3600.0)
        ext = "hr"
    elif s < 604800:
        val = (s / 86400.0)
        ext = "day"
    elif s < 31449600:
        val = (s / 604800.0)
        ext = "wk"
    else:
        val = (s / 31449600.0)
        ext = "yr"
    if abs(val - int(val)) < .000001:
        fmt = "%d"
    result = (fmt % val) + ext
    return result


interval_dict = OrderedDict([
    ("year", 365*86400), ("yr", 365*86400), ("y", 365*86400),
    ("week", 7*86400), ("wk", 7*86400),
    ("day", 86400),    ("d", 86400),
    ("hour", 3600), ("hr", 3600), ("h", 3600),
    ("ms", .001),  # ms before m so m doesn't steal the first letter
    ("min", 60), ("m", 60),
    ("sec", 1), ("s", 1),
    ])

def parse_pretty_seconds(s):
    """Convert internal string like 1M, 1Y3M, 3W to seconds.

    :type string: str
    :param string: Interval string like 1M, 1W, 1M3W4h2s...
        (s => seconds, m => minutes, h => hours, D => days, W => weeks, M => months, Y => Years).

    :rtype: int
    :return: The conversion in seconds of string.

    Based on: https://thomassileo.name/blog/2013/03/31/how-to-convert-seconds-to-human-readable-interval-back-and-forth-with-python/
    """
    interval_exc = "Bad interval format for {0}".format(s)

    interval_regex = re.compile("^(?P<value>[0-9.]+)(?P<unit>({0}))".format("|".join(list(interval_dict.keys()))))
    seconds = 0

    while s:
        match = interval_regex.match(s)
        if match:
            value, unit = int(match.group("value")), match.group("unit")
            if int(value) and unit in interval_dict:
                seconds += value * interval_dict[unit]
                s = s[match.end():]
            else:
                raise ValueError(interval_exc)
        else:
            raise ValueError(interval_exc)
    return seconds


def check_for_matching_lines(text, sre):
    """Return a list of lines that match the regular expression
    """
    cre = re.compile(sre)
    num_matched = 0
    num_unmatched = 0
    for line in text.splitlines(False):
        log.debug("processing %s" % line)
        match = cre.match(line)
        if match is None:
            if line.strip(): # ignore blank lines
                log.debug("unmatched: %s" % line)
                num_unmatched += 1
        else:
            num_matched += 1
    log.debug("%d matched, %d unmatched" % (num_matched, num_unmatched))
    return num_matched, num_unmatched


def parse_for_matching_lines(text, sre, group_indexes):
    """Return a list of values that match the regular expression. The groups
    listed in group_indexes are pulled out of each line and used in the
    returned array.
    """
    cre = re.compile(sre)
    matches = []
    num_unmatched = 0
    for line in text.splitlines(False):
        log.debug("processing %s" % line)
        match = cre.match(line)
        if match is None:
            if line.strip(): # ignore blank lines
                log.debug("unmatched: %s" % line)
                num_unmatched += 1
        else:
            row = []
            for i in group_indexes:
                row.append(match.group(i))
            matches.append(row)
    log.debug("%d matched, %d unmatched" % (len(matches), num_unmatched))
    return matches, num_unmatched


if __name__ == "__main__":
    import sys

    for file in sys.argv[1:]:
        fh = open(file)
        text = fh.read()
        log.debug("file=%s, tabsize=%d" % (file, guessSpacesPerIndent(text)))

        print((parse_int_label_dict(text)))
        print((parse_int_label_dict(text, allow_equal=True)))

    if False:
        print((parse_pretty_seconds("5m")))
        print((parse_pretty_seconds("5wk")))
        print((parse_pretty_seconds("5ms")))
        step_values = ['10m', '20m', '30m', '40m', '45m', '60m', '90m', '120m', '3hr', '4hr', '5hr', '6hr', '8hr', '10hr', '12hr', '16h', '24hr', '36hr', '48hr', '3d', '4d', '5d', '6d', '7d', '2wk', '3wk', '4wk']
        step_values_as_seconds = [parse_pretty_seconds(a) for a in step_values]
        print(step_values_as_seconds)
        print([pretty_seconds(a) for a in step_values_as_seconds])

# ^\s*([-+]?([1-8]?\d(\.\d+)?|90(\.0+)?))\s*[,\s]?\s*([-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?))

    re_latlon = r'^\s*(-(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))\s*[,\s]?\s*([-+]?(?:180(?:\.0+)?|(?:(?:1[0-7]\d)|(?:[1-9]?\d))(?:\.\d+)?))'
    re_lonlat = r'^\s*([-+]?(?:180(?:\.0+)?|(?:(?:1[0-7]\d)|(?:[1-9]?\d))(?:\.\d+)?))\s*[,\s]?\s*(-(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))'

    re_latlon = r'^\s*([-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))\s*[/,|\s]+\s*([-+]?(?:180(?:\.0+)?|(?:(?:1[0-7]\d)|(?:[1-9]?\d))(?:\.\d+)?))'
    re_lonlat = r'^\s*([-+]?(?:180(?:\.0+)?|(?:(?:1[0-7]\d)|(?:[1-9]?\d))(?:\.\d+)?))\s*[/|,\s]+\s*([-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))'

    text = """
-62.242001\t, 12.775000, 1.000
-28.990000  , 12.775000, 1.000
8.990000, 30.645000, 1.000
-4.669998, 31.774000, 102.000
0.500999   36.661999, 1.000
-43.978001\t28.400000, 1.000
-137.164001 | 25.445999, 60.000
33.2
-139.804001, 17.983000, 1.000
-144.109001, 22.204000, 1.000
23.44903 -ZZZZ
-50.821999, 20.202999, 97.000
-34.911236, 29.293791, 1.000






"""
    if True:
        matches, num_unmatched = parse_for_matching_lines(text, re_latlon)
        print([(m.group(1), m.group(2)) for m in matches])
        print(num_unmatched)

        matches, num_unmatched = parse_for_matching_lines(text, re_lonlat)
        print([(m.group(1), m.group(2)) for m in matches])
        print(num_unmatched)
