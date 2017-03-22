# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info


#### STC Interface

class STCInterface(object):
    """
    Methods that a data source object must implement in order to be
    compatible with the real STC used as the data source for
    text-based files.

    See U{the Yellowbrain guide to the
    STC<http://www.yellowbrain.com/stc/index.html>} for more info on
    the rest of the STC methods.
    """

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


class STCBinaryMixin(object):
    """Interface that major modes must implement to be editable with the HexEdit
    mode.
    """

    def GetBinaryData(self, start, end=-1):
        """Return the raw bytes between the given locations.
        
        @param start: starting offset
        @param end: ending offset, passing -1 means end of file
        """
        raise NotImplementedError

    def SetBinaryData(self, start, end, bytes):
        """Set raw bytes between the given locations.
        
        Note that bytes can be inserted or deleted if the length of the new
        byte string is different than the specified range.
        
        @param start: starting offset
        @param end: ending offset
        @param bytes: new bytes to replace existing data
        """
        raise NotImplementedError


class STCProxy(object):
    """Proxy object to defer requests to a real STC.

    Used to wrap a real STC but supply some custom methods.  This is
    used in the case where the major mode is using a real stc for its
    data storage, but not using the stc for display.  Because the
    major mode depends on an stc interface to manage the user
    interface (enabling/disabling buttons, menu items, etc.), a mode
    that doesn't use the stc for display still has to present an stc
    interface for this purpose.  So, wrapping the buffer's stc in this
    object and reassigning methods as appropriate for the display is
    the way to go.
    """

    def __init__(self, stc):
        self.stc = stc

    def __getattr__(self, name):
        # can't use self.stc.__dict__ because the stc is a swig object
        # and apparently swig attributes don't show up in __dict__.
        # So, this is probably slow.
        if hasattr(self.stc, name):
            return getattr(self.stc, name)
        raise AttributeError


class NonResidentSTC(STCInterface):
    """Non-memory-resident version of the STC.
    
    Base version of a non-memory resident storage space that
    implements the STC interface.
    """

    def __init__(self, parent=None, copy=None):
        self.filename = None

    def Destroy(self):
        pass


class UndoableItem(object):
    def undo(self, stc):
        """Override this in subclass to perform an undo operation
        
        The information needed to perform the undo must have been
        self- contained in the object that was saved by the call to
        L{UndoMixin.undoMixinSaveUndoableItem}
        """
        raise NotImplementedError

    def redo(self, stc):
        """Override this in subclass to perform a redo operation
        
        The information needed to perform the redo must have been
        self- contained in the object that was saved by the call to
        L{UndoMixin.undoMixinSaveUndoableItem}
        """
        raise NotImplementedError


class UndoMixin(object):
    """Mixin class to support undo operations in an STC that doesn't natively
    support them.
    
    """

    def __init__(self):
        self.EmptyUndoBuffer()

    def EmptyUndoBuffer(self):
        self._undo_list = []
        self._undo_save_point = 0
        self._undo_index = 0

    def CanUndo(self):
        return self._undo_index > 0

    def Undo(self):
        if self._undo_index > 0:
            self._undo_index -= 1
            obj = self._undo_list[self._undo_index]
            obj.undo(self)

    def CanRedo(self):
        return self._undo_index < len(self._undo_list)

    def Redo(self):
        if self._undo_index < len(self._undo_list):
            obj = self._undo_list[self._undo_index]
            obj.redo(self)
            self._undo_index += 1

    def SetSavePoint(self):
        self._undo_save_point = self._undo_index

    def GetModify(self):
        return self._undo_save_point != self._undo_index

    def undoMixinSaveUndoableItem(self, obj):
        """Save an item in the undo history.
        
        This method is used to save an item in the undo history.  When the user
        makes and edit and it is appropriate to have this edit added to the
        undo history, this method puts that edit in the undo history.
        
        The edit needs to be encapsulated by an object that is subclassed from
        L{UndoableItem}.  It must maintain enough details inside that object
        to be able to reverse the edit if the user chooses to undo the edit,
        and also needs to be able to reapply the edit should the user chose to
        redo it.
        
        The object itself is opaque to the L{UndoMixin}; the mixin just
        stores a list of objects in its undo history.  The object's
        L{undo} and L{redo} methods are passed the STC as a parameter.
        """
        # Truncate everything after the current index if we are not at the end
        # of the undo list
        if len(self._undo_list) > self._undo_index:
            self._undo_list = self._undo_list[:self._undo_index]

        self._undo_list.append(obj)
        self._undo_index += 1
