# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, time, codecs

import wx
import wx.stc

from cStringIO import StringIO

from stcinterface import *
from omnivore.utils.textutil import *
from omnivore.utils.clipboard import *

import logging
log = logging.getLogger(__name__)


class FoldNode:
    def __init__(self,level,start,end,text,parent=None,styles=[]):
        """Folding node as data for tree item."""
        self.parent     = parent
        self.level      = level
        self.start      = start
        self.end        = end
        self.text       = text
        self.styles     = styles #can be useful for icon detection
        self.children   = []

    def __str__(self):
        return "L%d s%d e%d %s" % (self.level, self.start, self.end, self.text.rstrip())


class PeppyBaseSTC(wx.stc.StyledTextCtrl, STCInterface):
    """The base class used as backend storage for files that fit in memory.
    
    Peppy uses the wx.stc.StyledTextCtrl (abbreviated STC in the peppy
    documentation) to store its files in memory.  Because the STC allows
    multiple views of the same file, we take advantage of this to prevent
    keeping multiple copies of the file for different views.  As described
    in L{MajorMode}, multiple STCs will keep themselves updated when the user
    makes change in another STC.
    
    Note that there is a difference in the STC stored in the L{Buffer} and any
    STCs that are used by the L{FundamentalMode} class.  There will always be
    at least two instances of STCs: one in the buffer that is the main backend
    storage, and the other in the major mode that provides the view.  They
    both point to the same data, but they are kept separate in order that
    major modes (i.e.  the views of the data) can change at will.
    
    This class performs the bookkeeping to keep the STC document pointers up to
    date when a new view is added.
    """
    eol2int = {'\r': wx.stc.STC_EOL_CR,
               '\r\n': wx.stc.STC_EOL_CRLF,
               '\n': wx.stc.STC_EOL_LF,
               }
    int2eol = {wx.stc.STC_EOL_CR: '\r',
               wx.stc.STC_EOL_CRLF: '\r\n',
               wx.stc.STC_EOL_LF: '\n',
               }

    def __init__(self, parent, refstc=None, copy=None, **kwargs):
        """Initialize the styled text control with peppy extensions.
        
        @param parent: wx.Control used as the parent control
        
        @keyword refstc: (default None) the parent STC, if any, to which
        this document object is linked.  Edits in one document are reflected
        transparently in all the linked documents.
        
        @keyword copy: (default None) STC from which to copy the text into the
        body of this STC
        """
        wx.stc.StyledTextCtrl.__init__(self, parent, -1, pos=(9000,9000), **kwargs)
        self.ClearAll()

        if refstc is not None:
            self.refstc = refstc
            self.docptr = self.refstc.docptr
            self.AddRefDocument(self.docptr)
            self.SetDocPointer(self.docptr)
            self.SetCodePage(65001) # set for unicode character display
            self.refstc.addSubordinate(self)
            log.debug("referencing document %s" % self.docptr)
        else:
            self.refstc = self
            self.docptr = self.CreateDocument()
            self.SetDocPointer(self.docptr)
            self.SetCodePage(65001) # set for unicode character display
            self.encoding = None # we don't know the encoding yet
            self.bom = None # we don't know if there is a Byte Order Mark
            log.debug("creating new document %s" % self.docptr)
            self.subordinates = []

            # If views can share info among similar classes, that info can be
            # stored here.
            self.stc_classes = []
            self.stc_class_info = {}

            if copy is not None:
                txt = copy.GetStyledText(0,copy.GetTextLength())
                dprint("copying %s from old stc." % repr(txt))
                self.AddStyledText(txt)
        self.maybe_undo_eolmode = None

    def updateSubordinateClasses(self):
        """Update the list of classes viewing this buffer."""
        classes = {}
        for view in self.subordinates:
            classes[view.__class__] = True
        self.stc_classses = classes.keys()

    def getSharedClassInfo(self, cls):
        """Get the dict that can be used to store data common to viewers of
        the specified class.
        """
        if cls not in self.refstc.stc_class_info:
            self.refstc.stc_class_info[cls] = {}
        return self.refstc.stc_class_info[cls]

    def addSubordinate(self,otherstc):
        self.subordinates.append(otherstc)
        self.updateSubordinateClasses()

    def removeDocumentView(self):
        """Remove the reference of this view from its parent document"""
        if self.refstc != self:
            self.refstc.subordinates.remove(self)
            self.refstc.updateSubordinateClasses()

    def open(self, buffer, message=None):
        """Open the file from the buffer and read in its contents.
        
        The open method is provided here in the STC and not in the buffer so
        that specialized STCs can provide their own load methods.  So far,
        this is only used in the L{NonResidentSTC} for files that are too
        large to fit in memory.
        """
        fh = buffer.getBufferedReader()
        self.readThreaded(fh, buffer, message)

    def revertEncoding(self, buffer, url=None, message=None, encoding=None, allow_undo=False):
        if url is None:
            url = buffer.url
        fh = vfs.open(url)
        if allow_undo:
            self.BeginUndoAction()
        self.ClearAll()
        self.readThreaded(fh, buffer, message)
        self.openSuccess(buffer, encoding=encoding)
        if allow_undo:
            self.EndUndoAction()
        else:
            self.EmptyUndoBuffer()

    def readThreaded(self, fh, buffer, message=None):
        self.refstc.tempstore = StringIO()
        if fh:
            # if the file exists, read the contents.
            length = vfs.get_size(buffer.url)
            log.debug("Loading %d bytes" % length)
            chunk = 65536
            if length/chunk > 100:
                chunk *= 4
            self.readFrom(fh, chunk=chunk, length=length, message=message)
            buffer.setInitialStateIsUnmodified()
        else:
            # if the file doesn't exist, the user has asked to create a new
            # file.  Peppy needs to reflect that it hasn't been saved by
            # setting its initial state to be 'modified'
            buffer.setInitialStateIsModified()

    def openSuccess(self, buffer, headersize=1024, encoding=None):
        bytes = self.tempstore.getvalue()

        self.resetText(bytes, headersize, encoding)

        del self.tempstore

    def resetText(self, bytes, headersize=1024, encoding=None):
        numbytes = len(bytes)
        if headersize > numbytes:
            headersize = numbytes
        header = bytes[0:headersize]

        if encoding:
            # Normalize the encoding name by running it through the codecs list
            self.refstc.encoding = codecs.lookup(encoding).name
        if not self.refstc.encoding:
            self.refstc.encoding, self.refstc.bom = detectEncoding(header)
        self.decodeText(bytes)
        log.debug("found encoding = %s" % self.refstc.encoding)
        self.detectLineEndings()

    def readFrom(self, fh, amount=None, chunk=65536, length=0, message=None):
        """Read a chunk of the file from the file-like object.
        
        Rather than reading the file in with a single call to fh.read(), it is
        broken up into segments.  It may take a significant amount of time to
        read a file, either if the file is really big or the file is loaded
        over a slow URI scheme.  The threaded load capability of peppy is used
        to display a progress bar that is updated after each segment is loaded,
        and also keeps the user interface responsive during a file load.
        """
        total = 0
        while amount is None or total<amount:
            txt = fh.read(chunk)
            log.debug("reading %d bytes from %s" % (len(txt), fh))

            if len(txt) > 0:
                total += len(txt)
                if message:
                    # Negative value will switch the progress bar to
                    # pulse mode
                    #Publisher().sendMessage(message, (total*100)/length)
                    pass

                if isinstance(txt, unicode):
                    # This only seems to happen for unicode files written
                    # to the mem: filesystem, but if it does happen to be
                    # unicode, there's no need to convert the data
                    self.refstc.encoding = "utf-8"
                    self.tempstore.write(unicode.encode('utf-8'))
                else:
                    self.tempstore.write(txt)
            else:
                # stop when we reach the end.  An exception will be
                # handled outside this class
                break

    def decodeText(self, bytes):
        """Check for the file encoding and convert in place.
        
        If the encoding is embedded in the file (through emacs "magic
        comments"), change the text from the binary representation into the
        specified encoding.
        """
        if self.refstc.encoding:
            try:
                unicodestring = encodedBytesToUnicode(bytes, self.refstc.encoding, self.refstc.bom)
                log.debug("unicodestring(%s) = %s bytes" % (type(unicodestring), len(unicodestring)))
                self.SetText(unicodestring)
                return
            except UnicodeDecodeError, e:
                log.debug("bad encoding %s:" % self.refstc.encoding)
                self.refstc.badencoding = self.refstc.encoding
                self.refstc.encoding = None
                self.refstc.bom = None

        # If there's no encoding or an error in the decoding, stuff the binary
        # bytes in the stc.  The only way to load binary data into scintilla
        # is to convert it to two bytes per character: first byte is the
        # content, 2nd byte is styling (which we set to zero)
        self.SetText('')
        styledtxt = '\0'.join(bytes)+'\0'
        self.AddStyledText(styledtxt)

    def prepareEncoding(self):
        """Prepare the file for encoding.
        
        This method provides a short-circuit of the writing process in case the
        encoding is bad.  This is a poor man's way of preventing a zero-length
        file due to a bad encoding, because should this method generate an
        exception, the file will never be opened for writing and therefore
        won't be truncated.
        """
        bytes = ""
        try:
            txt = self.GetText()
            encoding, bom = detectEncoding(txt)
            if encoding:
                log.debug("found encoding %s" % encoding)
                bytes = txt.encode(encoding)
                if encoding != self.refstc.encoding:
                    # If the encoding has changed, update it here
                    self.refstc.encoding = encoding
                    self.refstc.bom = bom
                    self.decodeText(bytes)
            elif self.refstc.encoding:
                if self.refstc.bom:
                    bytes = self.refstc.bom
                bytes += txt.encode(self.refstc.encoding)
            else:
                # Have to use GetStyledText because GetText will truncate the
                # string at the first zero character.
                numchars = self.GetTextLength()
                bytes = self.GetStyledText(0, numchars)[0:numchars*2:2]

            self.refstc.encoded = bytes
        except:
            self.refstc.encoded = None
            raise

    def openFileForWriting(self, url):
        return vfs.open_write(url)

    def writeTo(self, fh, url):
        """Writes a copy of the document to the provided file-like object.
        
        Note that peppy is not currently thread-enabled during file writing.
        """
        txt = self.refstc.encoded
        if txt is None:
            raise IOError("Invalid encoded string -- this should never happen")

        #dprint("writing %d bytes to %s" % (len(txt), fh))

        try:
            fh.write(txt)
        finally:
            # clean up temporary encoded version of the text
            self.refstc.encoded = None

    def closeFileAfterWriting(self, fh):
        fh.close()

    def getAutosaveTemporaryFilename(self, buffer):
        """Hook to allow STC to override autosave filename"""
        return wx.GetApp().autosave.getFilename(buffer.url)

    def getBackupTemporaryFilename(self, buffer):
        """Hook to allow STC to override backup filename"""
        return wx.GetApp().backup.getFilename(buffer.url)

    ## Additional functionality
    def checkUndoEOL(self):
        """Check to see if the last change was converting all EOL characters.
        
        The wx.stc.StyledTextCtrl doesn't directly store if the last undo/redo
        was the change in all of the end of line characters, so we have to
        check ourselves.
        """
        # Check to see if the eol mode has changed.
        if self.maybe_undo_eolmode is not None:
            if self.maybe_undo_eolmode['likely']:
                self.detectLineEndings(self.GetText())
                #Publisher().sendMessage('resetStatusBar')
            self.maybe_undo_eolmode = None

    def Undo(self):
        """Override of base Undo command to add our additional checks."""
        wx.stc.StyledTextCtrl.Undo(self)
        self.checkUndoEOL()

    def Redo(self):
        """Override of base Redo command to add our additional checks."""
        wx.stc.StyledTextCtrl.Redo(self)
        self.checkUndoEOL()

    ## STCInterface additions
    def CanCopy(self):
        return True

    def CanCut(self):
        return True

    def SelectAll(self):
        self.SetSelectionStart(0)
        self.SetSelectionEnd(self.GetLength())

    def GetBinaryData(self, start=0, end=-1):
        """Convenience function to get binary data out of the STC.
        
        The only way to get binary data out of the STC is to use the
        GetStyledText method and chop out every other byte.  Using the regular
        GetText method will stop at the first nul character.

        @param start: first text position
        @param end: last text position
        
        @returns: binary data between start and end-1, inclusive (just
        like standard python array slicing)
        """
        if end == -1:
            end = self.GetTextLength()
        return self.GetStyledText(start,end)[::2]

    def SetBinaryData(self, loc, locend, bytes):
        """Replace the binary data in the specified range.
        
        Given a start and end position, this method replaces the binary bytes
        with the given string of bytes.  Note that bytes can be inserted or
        deleted if the length of the new byte string is different than the
        specified range.
        """
        # FIXME: the set/replace selection can fail if we start or end in the
        # middle of a multi-byte sequence.  To properly handle this, we'd
        # have to search backwards and forwards to make sure that we aren't
        # splitting a UTF-8 sequence
        start = loc
        valid = False
        while not valid:
            try:
                self.GotoPos(start)
                valid = True
            except wx._core.PyAssertionError:
                log.debug("Trying back one... start=%d" % start)
                if start > 0:
                    start -= 1
        if start > 0:
            self.CmdKeyExecute(wx.stc.STC_CMD_CHARLEFTEXTEND)
        start = self.GetSelectionStart()
        end = locend
        valid = False
        while not valid:
            try:
                self.GotoPos(end)
                valid = True
            except wx._core.PyAssertionError:
                log.debug("Trying ahead one... end=%d" % end)
                if end < self.GetLength():
                    end += 1
        self.CmdKeyExecute(wx.stc.STC_CMD_CHARRIGHTEXTEND)
        end = self.GetSelectionEnd()
        data = self.GetStyledText(start, end)
        self.SetSelection(start, end)
        self.ReplaceSelection('')

        styled = '\0'.join(bytes) + '\0'
        gap1 = loc - start
        gap2 = gap1 + locend - loc
        replacement = data[:gap1 * 2] + styled + data[gap2 * 2:]
        log.debug("start=%d loc=%d locend=%d end=%d  data=%s styled=%s replace=%s" % (start, loc, locend, end, repr(data), repr(styled), repr(replacement)))
        self.AddStyledText(replacement)

    def GuessBinary(self,amount,percentage):
        """
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
        endpos=self.GetLength()
        if endpos>amount: endpos=amount
        bin=self.GetBinaryData(0,endpos)
        data = [ord(i) for i in bin]
        binary=0
        for ch in data:
            if (ch<8) or (ch>13 and ch<32) or (ch>126):
                binary+=1
        if binary>(endpos/percentage):
            return True
        return False

    def GetSelection2(self):
        """Get the current region, but don't return an empty last line if the
        cursor is at column zero of the last line.
        
        The STC seems to make entire line selections by placing the cursor
        on the left margin of the next line, rather than the end of the
        last highlighted line.  This causes any use of GetLineEndPosition
        to use this line with only the cursor to mean a real part of the
        selection, which is never what I indend, at least.  So, this version of
        GetSelection handles this case.
        """
        start, end = self.GetSelection()
        if start == end:
            return start, end
        if self.GetColumn(end) == 0:
            line = self.LineFromPosition(end - 1)
            newend = self.GetLineEndPosition(line)
            # If the new end is still greater than the start, then we'll assume
            # that this is going to work; otherwise, it wouldn't be possible to
            # select only the newline
            if newend > start:
                return start, newend
        return start, end

    def GetOneLineTarget(self):
        """Create a target encompassing the current line
        
        The STC seems to make entire line selections by placing the cursor
        on the left margin of the next line, rather than the end of the
        last highlighted line.
        """
        start, end = self.GetSelection()
        if start == end:
            line = self.LineFromPosition(start)
            start = self.PositionFromLine(line)
            end = self.GetLineEndPosition(line)
        else:
            start_line = self.LineFromPosition(start)
            end_line = self.LineFromPosition(end)
            # NOTE: The STC seems to make entire line selections by placing the
            # cursor on the left margin of the next line, rather than the end
            # of the last highlighted line.
            if end_line == start_line + 1 and self.GetColumn(end) == 0:
                start = self.PositionFromLine(start_line)
                end = self.GetLineEndPosition(end_line)
            else:
                # There is a selection, and it's more than one line
                return False
        self.SetTargetStart(start)
        self.SetTargetEnd(end)
        return True

    def GetLineRegion(self):
        """Get current region, extending to current line if no region
        selected.

        If there's a region selected, extend it if necessary to
        encompass full lines.  If no region is selected, create one
        from the current line.
        """
        start, end = self.GetSelection()
        if start == end:
            linestart = lineend = self.GetCurrentLine()
        else:
            linestart = self.LineFromPosition(start)
            lineend = self.LineFromPosition(end - 1)

        start -= self.GetColumn(start)
        end = self.GetLineEndPosition(lineend)
        self.SetSelection(start, end)
        return (linestart, lineend)

    def PasteAtColumn(self, paste=None):
        """Paste a rectangular selection at a particular column.
        
        This method inserts a previously cut or copied rectangular selection
        at a column.  If some lines in the STC are too short and end before
        the column, leading spaces are inserted so that the column is pasted
        correctly.
        """
        log.debug("rectangle=%s" % self.SelectionIsRectangle())
        start, end = self.GetSelection()
        log.debug("selection = %d,%d" % (start, end))

        line = self.LineFromPosition(start)
        col = self.GetColumn(start)
        log.debug("line = %d, col=%d" % (line, col))

        if paste is None:
            paste = GetClipboardText()
        self.BeginUndoAction()
        try:
            for insert in paste.splitlines():
                if line >= self.GetLineCount():
                    self.InsertText(self.GetTextLength(), self.getLinesep())
                start = pos = self.PositionFromLine(line)
                last = self.GetLineEndPosition(line)

                # FIXME: doesn't work with tabs
                if (pos + col) > last:
                    # need to insert spaces before the rectangular area
                    num = pos + col - last
                    insert = ' '*num + insert
                    pos = last
                else:
                    pos += col
                log.debug("before: (%d,%d) = '%s'" % (start,last,self.GetTextRange(start,last)))
                log.debug("inserting: '%s' at %d" % (insert, pos))
                self.InsertText(pos, insert)
                log.debug("after: (%d,%d) = '%s'" % (start,last+len(insert),self.GetTextRange(start,last+len(insert))))
                line += 1
        finally:
            self.EndUndoAction()

    def detectLineEndings(self, header=None):
        """Guess which type of line ending is used by the file."""
        def whichLinesep(text):
            # line ending counting function borrowed from PyPE
            crlf_ = text.count('\r\n')
            lf_ = text.count('\n')
            cr_ = text.count('\r')
            mx = max(lf_, cr_)
            if not mx:
                return os.linesep
            elif crlf_ >= mx/2:
                return '\r\n'
            elif lf_ is mx:
                return '\n'
            else:# cr_ is mx:
                return '\r'

        if header is None:
            header = self.GetText()
        linesep = whichLinesep(header)
        mode = self.eol2int[linesep]
        self.SetEOLMode(mode)

    def getNativeEOLMode(self):
        try:
            return self.eol2int[os.linesep]
        except KeyError:
            raise RuntimeError("Unsupported native line separator")

    def isNativeEOLMode(self):
        return self.GetEOLMode() == self.getNativeEOLMode()

    def forceNativeEOLMode(self):
        mode = self.getNativeEOLMode()
        self.ConvertEOLs(mode)

    def ConvertEOLs(self, mode):
        wx.stc.StyledTextCtrl.ConvertEOLs(self, mode)
        self.SetEOLMode(mode)

    def getLinesep(self):
        """Get the current line separator character.

        """
        mode = self.GetEOLMode()
        return self.int2eol[mode]

    def convertStringEOL(self, text):
        """Convert a string to the target EOL format of this STC"""
        target = self.getLinesep()
        if target == '\r':
            text = text.replace('\r\n', '\r').replace('\n', '\r')
        elif target == '\n':
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        else:
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
        return text

    # Styling stuff

    def showStyle(self, linenum=None):
        if linenum is None:
            linenum = self.GetCurrentLine()

        linestart = self.PositionFromLine(linenum)

        # actual indention of current line
        ind = self.GetLineIndentation(linenum) # columns
        pos = self.GetLineIndentPosition(linenum) # absolute character position

        # folding says this should be the current indention
        fold = self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE

        # get line without indention
        line = self.GetLine(linenum)
        dprint("linenum=%d fold=%d cursor=%d line=%s" % (linenum, fold, self.GetCurrentPos(), repr(line)))
##        for i in range(len(line)):
##            dprint("  pos=%d char=%s style=%d" % (linestart+i, repr(line[i]), self.GetStyleAt(linestart+i) ))

    def showLine(self, line, offset_from_top = 0):
        """Move the cursor to the specified line and show that line at the top
        of the screen.
        
        @param line: line number to display
        
        @keyword offset_from_top: (default 0) optional offset from the top of
        the screen.  The cursor will still be placed at the specified line, but
        the line will be offset C{offset_from_top} number of lines from the top.
        """
        # expand folding if any
        self.EnsureVisible(line)

        # Make line appear at the top of the screen.  ScrollToLine doesn't seem
        # to work when applied right after a GotoLine, but moving to the end
        # of the document and then back does seem to put the line at the top
        # of the screen
        self.GotoLine(self.GetLineCount())

        # If there is an offset from the top of the screen, some extra lines
        # are displayed between the top of the screen and the line with the
        # cursor.
        if offset_from_top > 0:
            self.GotoLine(max(0, line - offset_from_top))
        self.GotoLine(line)
#        dprint("After first GotoLine(%d): FirstVisibleLine = %d" % (line, self.GetFirstVisibleLine()))
#        self.ScrollToLine(line + self.LinesOnScreen() - 3)
#        dprint("After first ScrollToLine(%d): FirstVisibleLine = %d" % (line + self.LinesOnScreen() - 3, self.GetFirstVisibleLine()))
#        self.GotoLine(line)
#        dprint("After second GotoLine(%d): FirstVisibleLine = %d" % (line, self.GetFirstVisibleLine()))
        self.ScrollToColumn(0)

    # --- line indentation stuff

    def FoldAll(self):
        """Fold or unfold all items.
        
        Code borrowed from the wxPython demo
        """
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & wx.stc.STC_FOLDLEVELHEADERFLAG and \
               (level & wx.stc.STC_FOLDLEVELNUMBERMASK) == wx.stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        """Expand all folds.
        
        Code borrowed from the wxPython demo.
        """
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & wx.stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def GetFoldColumn(self, linenum):
        return self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE

    def GetPrevLineIndentation(self, linenum):
        for i in xrange(linenum-1, -1, -1):
            indent = self.GetLineIndentPosition(i)
            last = self.GetLineEndPosition(i)
            if indent<last:
                col = self.GetLineIndentation(i)
                log.debug("line=%d indent=%d (col=%d) last=%d" % (i, indent, col, last))
                return col, i
            log.debug("all blanks: line=%d indent=%d last=%d" % (i, indent, last))
        return 0, -1

    def GetIndentString(self, ind):
        if self.GetUseTabs():
            text = (ind*' ').replace(self.GetTabWidth()*' ', '\t')
        else:
            text = ind*' '
        #dprint("requested: %d, text=%s" % (ind, repr(text)))
        return text

    ##### Utility methods for modifying the contents of the STC
    def addLinePrefixAndSuffix(self, start, end, prefix='', suffix=''):
        """Add a prefix and/or suffix to the line specified by start and end.

        Method to add characters to the start and end of the line. This is
        typically called within a loop that adds comment characters to the
        line.  start and end are assumed to be the endpoints of the
        current line, so no further checking of the line is necessary.

        @param start: first character in line
        @param end: last character in line before line ending
        @param prefix: optional prefix for the line
        @param suffix: optional suffix for the line

        @returns: new position of last character before line ending
        """
        log.debug("commenting %d - %d: '%s'" % (start, end, self.GetTextRange(start,end)))
        slen = len(prefix)
        self.InsertText(start, prefix)
        end += slen

        elen = len(suffix)
        if elen > 0:
            self.InsertText(end, suffix)
            end += elen
        return end + len(self.getLinesep())

    def removeLinePrefixAndSuffix(self, start, end, prefix='', suffix=''):
        """Remove the specified prefix and suffix of the line.

        Method to remove the specified prefix and suffix characters from the
        line specified by start and end.  If the prefix or suffix doesn't match
        the characters in the line, nothing is removed. This is typically
        called within a loop that adds comment characters to the line.  start
        and end are assumed to be the endpoints of the current line, so no
        further checking of the line is necessary.

        @param start: first character in line
        @param end: last character in line before line ending
        @param prefix: optional prefix for the line
        @param suffix: optional suffix for the line

        @returns: new position of last character before line ending
        """
        log.debug("uncommenting %d - %d: '%s'" % (start, end, self.GetTextRange(start,end)))
        slen = len(prefix)
        if self.GetTextRange(start, start+slen) == prefix:
            self.SetSelection(start, start+slen)
            self.ReplaceSelection("")
            end -= slen

        elen = len(suffix)
        if elen > 0:
            if self.GetTextRange(end-elen, end) == suffix:
                self.SetSelection(end-elen, end)
                self.ReplaceSelection("")
                end -= elen
        return end + len(self.getLinesep())

    # Word stuff (for spelling, etc.)
    def getWordFromPosition(self, pos):
        end = self.WordEndPosition(pos, True)
        start = self.WordStartPosition(pos, True)
        word = self.GetTextRange(start, end)
        return (word, start, end)

    def selectBraces(self, pos=None, braces=None):
        """Given a point, find the region contained by the innermost set of braces.
        
        If not specified, all types of braces (e.g.  parens, brackets, curly
        braces) are matched.  Otherwise, only the specified types of braces
        are matched.
        
        @param pos: starting position
        @param braces: string containing brace types
        @return: True if valid region found
        @side-effect: selects region if valid
        """
        if pos is None:
            pos = self.GetCurrentPos()

        if braces is None:
            braces = "([{"
        braces = braces.replace(')', '(').replace(']', '[').replace('}', '{')
        matching = {'(': ')', ')': '(',
                    '[': ']', ']': '[',
                    '{': '}', '}': '{'}

        # use regex to search forward for all brace chars
        pattern = "[\(\[\{\)\]\}]"
        pairs = {u'(': 0, u'[': 0, u'{': 0}
        braceopen = ''
        i = pos
        last = self.GetLength()
        while i < last:
            i = self.FindText(i, last, pattern, wx.stc.STC_FIND_REGEXP)
            if i < 0:
                break
            c = self.GetTextRange(i, i+1)
            s = self.GetStyleAt(i)
            if self.isStyleComment(s) or self.isStyleString(s):
                # Skip matches inside strings
                i += 1
                continue
            if c in u')]}':
                c = matching[c]
                pairs[c] -= 1
                #dprint("-->: closing brace %s at %d: pairs=%s" % (matching[c], i, str(pairs)))
                if pairs[c] < 0:
                    # found an unmatched closing brace.  We're done matching
                    # in this direction, but we have to check if there's a
                    # nesting error.  If all others are zero, we have our
                    # match.  Otherwise, there's some nesting error and we
                    # won't be able to do the search.
                    count = 0
                    for k,v in pairs.iteritems():
                        if k == c:
                            continue
                        count += v
                    if count == 0:
                        # No nesting error, so mark the brace type
                        braceopen = c
                    break
            else:
                # found an opening brace, so now we have to do a search for
                # more brace pairs till we find a closing brace.  We could go
                # many levels of nesting before we find the closing.
                pairs[c] += 1
                #dprint("-->: opening brace %s at %d: pairs=%s" % (c, i, str(pairs)))
            i += 1

        #dprint("brace type = %s at %d" % (braceopen, i))
        last = i

        # Can't use regular expressions searching backward (scintilla
        # limitation), so have to use the slow char-by-char method.
        i = pos
        pairs = {u'(': 0, u'[': 0, u'{': 0}
        while i > 0:
            i -= 1
            c = self.GetTextRange(i, i+1)
            if c in matching:
                if c in u')]}':
                    c = matching[c]
                    pairs[c] += 1
                    #dprint("<--: closing brace %s at %d: pairs=%s" % (matching[c], i, str(pairs)))
                else:
                    pairs[c] -= 1
                    #dprint("<--: opening brace %s at %d: pairs=%s" % (c, i, str(pairs)))
                    if pairs[c] < 0:
                        # found an unmatched opening brace.  Check nesting
                        # and return
                        count = 0
                        for k,v in pairs.iteritems():
                            if k == c:
                                continue
                            count += v
                        if count == 0:
                            # No nesting error, so we have the range
                            #dprint("found match of %s" % braceopen)
                            self.SetSelection(i, last + 1)
                            return True
                        return False
        return False

    def findSameStyle(self, pos=None):
        """Given a point, find the region that has the same style
        
        @param pos: starting position
        @return: tuple of start, end position
        """
        if pos is None:
            pos = self.GetCurrentPos()

        mask = (2**self.GetStyleBits()) - 1
        style = self.GetStyleAt(pos) & mask

        i = pos
        last = self.GetLength()
        while i < last:
            s = self.GetStyleAt(i) & mask
            if s != style:
                break
            i += 1
        last = i

        i = pos
        while i > 0:
            s = self.GetStyleAt(i - 1) & mask
            if s != style:
                break
            i -= 1
        first = i
        return first, last

    ##### Revert hooks
    def getViewPositionData(self):
        return {'top': self.GetFirstVisibleLine(),
                'pos': self.GetCurrentPos(),
                'line': self.GetCurrentLine(),
                }

    def setViewPositionData(self, data):
        if 'top' in data:
            line = min(data['top'], self.GetLineCount() - 1)
            self.ScrollToLine(line)
        if 'line' in data:
            line = min(data['line'], self.GetLineCount() - 1)
            self.showLine(line)
        if 'pos' in data:
            pos = min(data['pos'], self.GetLength() - 1)
            self.GotoPos(pos)

            # Hack to fix #505.  For some reason, the internal scintilla cursor
            # column isn't correct after setting a cursor position manually.
            # Moving the cursor left and then back seems to fix it.
            if pos > 0:
                self.CmdKeyExecute(wx.stc.STC_CMD_CHARLEFT)
                self.CmdKeyExecute(wx.stc.STC_CMD_CHARRIGHT)


class PeppySTC(PeppyBaseSTC):
    """Base class used by major modes that use the STC.
    
    This class contains all the GUI callbacks and mouse bindings on top of
    L{PeppyBaseSTC}
    """

    def __init__(self, parent, refstc=None, copy=None, **kwargs):
        """Initialize the styled text control with peppy extensions.
        
        @param parent: wx.Control used as the parent control
        
        @keyword refstc: (default None) the parent STC, if any, to which
        this document object is linked.  Edits in one document are reflected
        transparently in all the linked documents.
        
        @keyword copy: (default None) STC from which to copy the text into the
        body of this STC
        
        @keyword cmd_key_clear_all: (default True) boolean value to prevent
        the normal call to CmdKeyClearAll.  Normally CmdKeyClearAll is called
        which removes all the default scintilla control keys because the peppy
        actions are used in place.  In rare cases, for example the Editra
        L{StyleEditor}, the scintilla actions are left in place because I've
        not bothered to convert the style editor to use peppy actions.
        """
        if 'cmd_key_clear_all' in kwargs:
            cmd_key_clear_all = kwargs['cmd_key_clear_all']
            del kwargs['cmd_key_clear_all']
        else:
            cmd_key_clear_all = True
        PeppyBaseSTC.__init__(self, parent, refstc=refstc, copy=copy, **kwargs)

        # Only bind events on STCs used as user interface elements.  The
        # reference STC that is not shown doesn't have any way for the user to
        # generate events on it, so event bindings aren't needed.  Plus, this
        # can lead to multiple events and problems deleting the view (bug #770)
        if refstc is not None:
            self.addSTCEventBindings()

        self.modified_callbacks = []

        # Remove all default scintilla keybindings so they will be replaced by
        # peppy actions.
        if cmd_key_clear_all:
            self.CmdKeyClearAll()

        self.debug_dnd=False

    def addSTCEventBindings(self):
        self.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(wx.stc.EVT_STC_DRAG_OVER, self.OnDragOver)
        self.Bind(wx.stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMousePaste)
        self.Bind(wx.EVT_LEFT_UP, self.OnSelectionEnd)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModified)

    def sendEvents(self,evt):
        """
        Send an event to all subordinate STCs
        """
        for otherstc in self.subordinates:
            log.debug("sending event %s to %s" % (evt,otherstc))
            wx.PostEvent(otherstc,evt())

    def addUpdateUIEvent(self, callback):
        self.Bind(wx.stc.EVT_STC_UPDATEUI, callback)

    def addDocumentChangeEvent(self, callback):
        self.Bind(wx.stc.EVT_STC_CHANGE, callback)

    def removeDocumentChangeEvent(self):
        self.Unbind(wx.stc.EVT_STC_CHANGE)

    def OnDestroy(self, evt):
        """
        Event handler for EVT_WINDOW_DESTROY. Preserve the clipboard
        contents can be preserved after the window is destroyed so
        that other apps can still grab it.

        @param evt: event
        """
        wx.TheClipboard.Flush()
        evt.Skip()

    def OnMouseWheel(self, evt):
        """Handle mouse wheel scrolling.
        """
        mouse = wx.GetApp().mouse
        log.debug("Wheel! delta=%s rotation=%s" % (evt.GetWheelDelta(), evt.GetWheelRotation()))
        if mouse.classprefs.mouse_wheel_scroll_style == 'lines':
            num = mouse.classprefs.mouse_wheel_scroll_lines
        else:
            num = self.LinesOnScreen()
            if mouse.classprefs.mouse_wheel_scroll_style == 'half':
                num /= 2
        if evt.GetWheelRotation() > 0:
            # positive means scrolling up, which is a negative number of lines
            # to scroll
            num = -num
        self.LineScroll(0, num)
        #evt.Skip()

    def OnMousePaste(self, evt):
        """Paste the primary selection (on unix) at the mouse cursor location
        
        This currently supports only the primary selection (not the normal
        cut/paste clipboard) from a unix implementation.
        """
        pos = self.PositionFromPoint(wx.Point(evt.GetX(), evt.GetY()))
        #print("x=%d y=%d pos=%d" % (evt.GetX(), evt.GetY(), pos))
        if pos != wx.stc.STC_INVALID_POSITION:
            text = GetClipboardText(True)
            if text:
                text = self.convertStringEOL(text)
                self.BeginUndoAction()
                self.InsertText(pos, text)
                self.GotoPos(pos + len(text))
                self.EndUndoAction()

    def OnSelectionEnd(self, evt):
        """Copy the selected region into the primary selection
        
        This currently supports unix only, because it depends on the primary
        selection of the clipboard.
        """
        start, end = self.GetSelection()
        if start != end:
            text = self.GetTextRange(start, end)
            SetClipboardText(text, True)
        evt.Skip()

    def OnStartDrag(self, evt):
        log.debug("OnStartDrag: %d, %s\n"
                       % (evt.GetDragAllowMove(), evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragAllowMove(False)     # you can prevent moving of text (only copy)
            evt.SetDragText("DRAGGED TEXT") # you can change what is dragged
            #evt.SetDragText("")             # or prevent the drag with empty text

    def OnDragOver(self, evt):
        log.debug(
            "OnDragOver: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
            % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult())
            )

        if self.debug_dnd and evt.GetPosition() < 250:
            evt.SetDragResult(wx.DragNone)   # prevent dropping at the beginning of the buffer

    def OnDoDrop(self, evt):
        log.debug("OnDoDrop: x,y=(%d, %d)  pos: %d  DragResult: %d\n"
                       "\ttext: %s\n"
                       % (evt.GetX(), evt.GetY(), evt.GetPosition(), evt.GetDragResult(),
                          evt.GetDragText()))

        if self.debug_dnd and evt.GetPosition() < 500:
            evt.SetDragText("DROPPED TEXT")  # Can change text if needed
            #evt.SetDragResult(wx.DragNone)  # Can also change the drag operation, but it
                                             # is probably better to do it in OnDragOver so
                                             # there is visual feedback

            #evt.SetPosition(25)             # Can also change position, but I'm not sure why
                                             # you would want to...

    def OnModified(self, evt):
        # NOTE: on really big insertions, evt.GetText can cause a
        # MemoryError on MSW, so I've commented this dprint out.
        #log.debug("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))

        # Since the stc doesn't store the EOL state as an undoable
        # parameter, we have to check for it.
        mod = evt.GetModificationType()
        if mod & (wx.stc.STC_PERFORMED_UNDO | wx.stc.STC_PERFORMED_REDO) and mod & (wx.stc.STC_MOD_INSERTTEXT | wx.stc.STC_MOD_DELETETEXT):
            text = evt.GetText()
            if self.maybe_undo_eolmode is None:
                self.maybe_undo_eolmode = {'total': 0, 'linesep': 0, 'likely': False}
            stats = self.maybe_undo_eolmode
            stats['total'] += 1
            if text == '\n' or text == '\r':
                log.debug("found eol char")
                stats['linesep'] += 1
            if mod & wx.stc.STC_LASTSTEPINUNDOREDO:
                log.debug("eol summary: %s" % stats)
                if stats['linesep'] == stats['total'] and stats['linesep'] >= self.GetLineCount()-1:
                    log.debug("likely that this is a eol change")
                    stats['likely'] = True
        elif mod & wx.stc.STC_MOD_CHANGEFOLD:
            self.OnFoldChanged(evt)
        for cb in self.modified_callbacks:
            cb(evt)
        evt.Skip()

    def addModifyCallback(self, func):
        self.modified_callbacks.append(func)

    def removeModifyCallback(self, func):
        if func in self.modified_callbacks:
            self.modified_callbacks.remove(func)

    def OnFoldChanged(self, evt):
        pass

    def OnUpdateUI(self, evt):
        log.debug("(%s) at %d: text=%s" % (self.transModType(evt.GetModificationType()),evt.GetPosition(), repr(evt.GetText())))
        evt.Skip()

    def transModType(self, modType):
        st = ""
        table = [(wx.stc.STC_MOD_INSERTTEXT, "InsertText"),
                 (wx.stc.STC_MOD_DELETETEXT, "DeleteText"),
                 (wx.stc.STC_MOD_CHANGESTYLE, "ChangeStyle"),
                 (wx.stc.STC_MOD_CHANGEFOLD, "ChangeFold"),
                 (wx.stc.STC_PERFORMED_USER, "UserFlag"),
                 (wx.stc.STC_PERFORMED_UNDO, "Undo"),
                 (wx.stc.STC_PERFORMED_REDO, "Redo"),
                 (wx.stc.STC_LASTSTEPINUNDOREDO, "Last-Undo/Redo"),
                 (wx.stc.STC_MOD_CHANGEMARKER, "ChangeMarker"),
                 (wx.stc.STC_MOD_BEFOREINSERT, "B4-Insert"),
                 (wx.stc.STC_MOD_BEFOREDELETE, "B4-Delete")
                 ]

        for flag,text in table:
            if flag & modType:
                st = st + text + " "

        if not st:
            st = 'UNKNOWN'

        return st

    def showInitialPosition(self, url, options=None):
        log.debug(u"url=%s scheme=%s auth=%s path=%s query=%s fragment=%s" % (url, url.scheme, url.authority, url.path, url.query, url.fragment))
        if url.fragment:
            line = int(url.fragment)
            line -= self.classprefs.line_number_offset
            self.showLine(line)
        if options:
            self.setViewPositionData(options)
