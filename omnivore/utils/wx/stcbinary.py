# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info

import numpy as np

from stcinterface import STCInterface, STCBinaryMixin


class BinarySTC(STCInterface, STCBinaryMixin):
    """
    Methods that a data source object must implement in order to be
    compatible with the real STC used as the data source for
    text-based files.

    See U{the Yellowbrain guide to the
    STC<http://www.yellowbrain.com/stc/index.html>} for more info on
    the rest of the STC methods.
    """

    def __init__(self):
        self.data = None

    def GetReadOnly(self):
        """Is the instance read-only (non-editable) or editable?"""
        return False

    def CanSave(self):
        """Can this STC instance save its contents?"""
        return True

    def Clear(self):
        pass

    def CanCopy(self):
        return False

    def Copy(self):
        pass

    def CanCut(self):
        return False

    def Cut(self):
        pass

    def CanPaste(self):
        return False

    def Paste(self):
        pass

    def EmptyUndoBuffer(self):
        pass

    def CanUndo(self):
        return False

    def Undo(self):
        pass

    def CanRedo(self):
        return False

    def Redo(self):
        pass

    def SetSavePoint(self):
        pass

    def GetText(self):
        return ''

    def GetLength(self):
        if self.data is not None:
            return self.data.size
        return 0

    GetTextLength = GetLength

    def GetModify(self):
        return False

    def CreateDocument(self):
        return "notarealdoc"

    def SetDocPointer(self,ptr):
        pass

    def ReleaseDocument(self,ptr):
        pass

    def AddRefDocument(self,ptr):
        pass

    def GuessBinary(self,amount,percentage):
        return False

    def getShortDisplayName(self, url):
        """Return a short name for display in tabs or other context without
        needing a pathname.
        """
        return url.path.get_name()

    def open(self, buffer, message=None):
        """Read from the specified url to populate the STC.
        
        Abstract method that subclasses use to read data into the STC.  May be
        called from a thread, so don't process any GUI actions here.

        buffer: buffer object used to read the file
        
        message: optional message used to update a progress bar
        """
        pass

    def revertEncoding(self, buffer, url=None, message=None, encoding=None, allow_undo=False):
        """Revert the file to the last saved state.
        
        @param buffer: buffer object used to read the file
        
        @param url: optional alternate URL, which if present means that the
        file should be reverted from the this URL instead of the original one.
        
        @param message: optional message used to update a progress bar
        
        @param encoding: optional encoding to attempt to convert from
        
        @param allow_undo: optional argument that if True and the STC is capable
        of it, allows the revert operation to be undoable.  If False or the
        STC isn't capable of undoing a revert, this parameter is ignored.
        """
        pass

    def readThreaded(self, fh, buffer, message=None):
        """Read from filehandle, converting as necessary.
        
        This may be called from a background thread, so no direct interaction
        with the GUI is allowed.  Any communication for progress bars needs to
        be done through the message that's passed in, using pubsub like::
        
            Publisher().sendMessage(message, percent)
        
        where percent is an integer from 0 to 100 indicating the amount of the
        file that has been successfully processed.  A value of -1 can be used
        to indicate that an unknown amount of data remains.

        @param fh: file-like object used to load the file
        @param buffer: L{Buffer} object containing information about the file
        @param message: optional pubsub message to be sent with progress
        """
        pass

    def openSuccess(self, buffer):
        """Called after a file has been successfully opened.
        
        This is called by the GUI thread, so can update any GUI elements here.
        """
        pass

    def getAutosaveTemporaryFilename(self, buffer):
        """Hook to allow STC to specify autosave filename"""
        pass

    def getBackupTemporaryFilename(self, buffer):
        """Hook to allow STC to override backup filename"""
        pass

    def prepareEncoding(self):
        """Convert the raw bytes in the file to the correct encoding before
        writing.
        
        """
        pass

    def openFileForWriting(self, url):
        """Return a file handle that has been opened for writing"""
        return None

    def writeTo(self, fh, url):
        """Write to filehandle, converting as necessary

        @param fh: file-like object to which the data should be saved
        @param url: the url that was used to open the file-like object
        """
        pass

    def closeFileAfterWriting(self, fh):
        """Close the opened file handle and perform any other cleanup"""
        pass

    def getProperties(self):
        """Return a list of properties to be displayed as text to the user
        
        @return: list of (name, value) pairs
        """
        return []

    def showStyle(self, linenum=None):
        """Debugging routine to show the styling information on a line.

        Print styling information to stdout to aid in debugging.
        """
        pass

    def GetFoldLevel(self, line):
        """Return fold level of specified line.

        Return fold level of line, which seems to be the number of spaces used
        to indent the line, plus an offset and shifted by 2^10
        """
        return 1024

    def GetFoldColumn(self, line):
        """Return column number of folding.

        Return column number of the current fold level.
        """
        return 0

    def GetPrevLineIndentation(self, line):
        """Get the indentation of the line before the specified line.

        Return a tuple containing the number of columns of indentation
        of the first non-blank line before the specified line, and the
        line number of the line that it found.
        """
        return 0, -1

    def GotoPos(self, pos):
        """Move the cursor to the specified position and scroll the
        position into the view if necessary.
        """
        pass

    def addUpdateUIEvent(self, callback):
        """Add the equivalent to STC_UPDATEUI event for UI changes.

        The STC supplies the EVT_STC_UPDATEUI event that fires for
        every change that could be used to update the user interface:
        a text change, a style change, or a selection change.  If the
        editing (viewing) window does not use the STC to display
        information, you should supply the equivalent event for the
        edit window.
        
        @param callback: event handler to execute on event
        """
        pass

    def addDocumentChangeEvent(self, callback):
        """Add the equivalent to EVT_STC_CHANGE event for document changes.

        The STC supplies the EVT_STC_CHANGE event that fires for every change
        to the contents of the document.  If you want peppy to be able to show
        indications that the document has been modified (which also allows
        peppy to display a dialog prompting for unsaved changes), register an
        event handler here that calls the specified callback when the document
        is changed.
        
        @param callback: event handler to execute on event
        """
        pass

    def removeDocumentChangeEvent(self):
        """Remove the document change event.
        
        The complement of L{addDocumentChangeEvent}, this is needed for example
        during revert processing so that all the intermediate changes don't
        generate change events that could propagate to user-level callbacks
        like the code explorer.
        """
        pass

    def GetBytes(self, start, end=-1):
        """Return the raw bytes between the given locations.
        
        @param start: starting offset
        @param end: ending offset, passing -1 means end of file
        """
        return self.data[start:end].tostring()

    def SetBytes(self, start, end, bytes):
        """Set raw bytes between the given locations.
        
        Note that bytes can be inserted or deleted if the length of the new
        byte string is different than the specified range.
        
        @param start: starting offset
        @param end: ending offset
        @param bytes: new bytes to replace existing data
        """
        bytes = np.fromstring(bytes, dtype=np.uint8)
        self.data[start:end] = bytes

    def SetBinary(self, data):
        self.data = np.fromstring(data, dtype=np.uint8)
        self.EmptyUndoBuffer()
