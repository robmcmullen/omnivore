"""General purpose event handling routines.

From public domain code by Marcus von Appen, described at:
https://python-utilities.readthedocs.io/en/latest/events.html
"""
import weakref

__all__ = ["EventHandler"]

import logging
log = logging.getLogger(__name__)


class Event(list):
    def __init__(self, sender, *args, **kwargs):
        self._sender = sender
        self[:] = args
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def sender(self):
        return self._sender


class EventHandler:
    """A simple event handling class, which manages callbacks to be
    executed.
    """
    event_class = Event

    def __init__(self, sender, event_class=None, debug=False):
        self.callbacks = []
        self.sender = sender
        if not debug:
            debug = log.getEffectiveLevel() <= logging.DEBUG
        self.debug = debug

    def __call__(self, *args, **kwargs):
        """Executes all callbacks.

        Executes all connected callbacks in the order of addition,
        passing the sender of the EventHandler as first argument and the
        optional args as second, third, ... argument to them.
        """
        results = []
        remove_indexes = []
        evt = self.event_class(self.sender, *args, **kwargs)
        for i, ref in enumerate(self.callbacks):
            callback = ref()
            if callback is None:
                if self.debug:
                    print(f"EventHandler {self.sender}: callback {ref} deleted; removing from callback list")
                remove_indexes.append(i)
            else:
                if self.debug:
                    print(f"EventHandler {self.sender}: calling {callback}, args={args}")
                result = callback(evt)
                results.append(result)
        try:
            while True:
                i = remove_indexes.pop()
                del self.callbacks[i]
        except IndexError:
            pass
        return results

    def __iadd__(self, callback):
        """Adds a callback to the EventHandler."""
        self.add(callback)
        return self

    def __isub__(self, callback):
        """Removes a callback from the EventHandler."""
        self.remove(callback)
        return self

    def __len__(self):
        """Gets the amount of callbacks connected to the EventHandler."""
        return len(self.callbacks)

    def __getitem__(self, index):
        return self.callbacks[index]

    def __setitem__(self, index, value):
        self.callbacks[index] = value

    def __delitem__(self, index):
        del self.callbacks[index]

    def add(self, callback):
        """Adds a callback to the EventHandler."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        if hasattr(callback, "__self__"):
            # bound methods are ephemeral objects so weak refs can't keep them
            ref = weakref.WeakMethod(callback)
            if self.debug:
                print(f"EventHandler {self.sender}: {callback} is a bound method; using WeakMethod")
        else:
            ref = weakref.ref(callback)
            if self.debug:
                print(f"EventHandler {self.sender}: {callback} using a normal weak reference")
        if self.debug:
            print(f"EventHandler {self.sender}: adding {callback}, ref={ref}")
        self.callbacks.append(ref)

    def remove(self, callback):
        """Removes a callback from the EventHandler."""
        if self.debug:
            print(f"EventHandler {self.sender}: removing {callback}")
        for i, ref in enumerate(self.callbacks):
            if ref() == callback:
                if self.debug:
                    print(f"EventHandler {self.sender}: found {callback} at {i}")
                del self.callbacks[i]
                break
        else:
            raise ValueError(f"EventHandler {self.sender}: callback {callback} not found")
