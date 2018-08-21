import os
import tempfile

import numpy as np

from ..persistence import Serializable

import logging
log = logging.getLogger(__name__)


class History(Serializable):
    serializable_attributes = ['input_raw', 'output_raw', 'frame_count']
    serializable_computed = {'input_raw', 'output_raw'}

    def __init__(self):
        self.history = self.calc_history_iterable()

    def calc_history_iterable(self):
        return dict()

    ##### Serialization

    def restore_computed_attributes(self, state):
        Debugger.restore_computed_attributes(self, state)
        self.input_raw[:] = state['input_raw']
        self.restore_state(state['output_raw'])

    ##### Storage indexes

    def __len__(self):
        return len(self.history)

    def is_memorable(self, frame_number):
        return frame_number % 10 == 0

    def get_previous_frame(self, frame_cursor):
        n = frame_cursor - 1
        while n > 0:
            if n in self.history:
                return n
            n -= 1
        raise IndexError("No previous frame")

    def get_next_frame(self, frame_cursor):
        n = frame_cursor + 1
        largest = max(self.history.keys())
        while n < largest:
            if n in self.history:
                return n
            n += 1
        raise IndexError("No next frame")

    ##### Storage

    def save_frame(self, frame_number, data):
        # History is saved in a big list, which will waste space for empty
        # entries but makes things extremely easy to manage. Simply delete
        # a history entry by setting it to NONE.
        frame_number = int(frame_number)
        self.history[frame_number] = data

    ##### Retrieval

    def __getitem__(self, index):
        try:
            index = int(index)
        except TypeError:
            try:
                return [self.history[i] for i in index]
            except TypeError:
                raise TypeError("argument must be a slice or an integer")
        else:
            if index < 0:
                index += len( self )
            return self.history[index]  # will raise IndexError here

    def get_frame(self, frame_number):
        frame_number = int(frame_number)
        raw = self.history[frame_number]
        return raw

    ##### Compact

    def decimate(self):
        """Remove old history items according to an algorithm that discards
        some portion of the older history as time goes on
        """
        pass
