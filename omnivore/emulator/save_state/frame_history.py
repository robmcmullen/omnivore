import os
import tempfile

import numpy as np

from ...utils.persistence import Serializable

import logging
log = logging.getLogger(__name__)


class FrameHistory(Serializable):
    name = None

    serializable_attributes = ['frame_history']
    serializable_computed = {'frame_history'}

    def __init__(self):
        self.frame_history = self.calc_history_iterable()

    def calc_history_iterable(self):
        return dict()

    ##### Serialization

    def calc_computed_attribute(self, key):
        if key == 'frame_history':
            return [list(a) for a in self.frame_history.items()]
        return getattr(self, key).copy()

    def restore_computed_attributes(self, state):
        self.frame_history = self.calc_history_iterable()
        for frame_number, data in state['frame_history']:
            self.frame_history[frame_number] = data

    ##### Storage indexes

    def __len__(self):
        return len(self.frame_history)

    def __iter__(self):
        keys = sorted(self.frame_history.keys())
        for k in keys:
            yield self.frame_history[k]

    def keys(self):
        return sorted(self.frame_history.keys())

    def is_memorable(self, frame_number):
        return frame_number % 10 == 0

    def get_previous_frame(self, frame_cursor):
        n = frame_cursor - 1
        while n > 0:
            if n in self.frame_history:
                return n
            n -= 1
        raise IndexError("No previous frame")

    def get_next_frame(self, frame_cursor):
        n = frame_cursor + 1
        largest = max(self.frame_history.keys())
        while n < largest:
            if n in self.frame_history:
                return n
            n += 1
        raise IndexError("No next frame")

    ##### Storage

    def save_frame(self, frame_number, data):
        # History is saved in a big list, which will waste space for empty
        # entries but makes things extremely easy to manage. Simply delete
        # a history entry by setting it to NONE.
        frame_number = int(frame_number)
        self.frame_history[frame_number] = data

    ##### Retrieval

    def __getitem__(self, index):
        try:
            index = int(index)
        except TypeError:
            try:
                return [self.frame_history[i] for i in index]
            except TypeError:
                raise TypeError("argument must be a slice or an integer")
        else:
            if index < 0:
                index += len( self )
            return self.frame_history[index]  # will raise IndexError here

    def get_frame(self, frame_number):
        frame_number = int(frame_number)
        raw = self.frame_history[frame_number]
        return raw

    ##### Compact

    def decimate(self):
        """Remove old history items according to an algorithm that discards
        some portion of the older history as time goes on
        """
        pass
