import os
import tempfile

import numpy as np

from .persistence import Serializable

import logging
log = logging.getLogger(__name__)


class RestartTree(Serializable):
    name = None

    serializable_attributes = ['restarts']

    def __init__(self):
        self.emulator_start = Restart(0, None)
        self.restarts = [self.emulator_start]

    #### dunder methods

    def __len__(self):
        return len(self.restarts)

    def __iter__(self):
        for r in self.restarts:
            yield r

    def __getitem__(self, index):
        try:
            index = int(index)
        except TypeError:
            try:
                return [self.restarts[i] for i in index]
            except TypeError:
                raise TypeError("argument must be a slice or an integer")
        else:
            if index < 0:
                index += len( self )
            return self.restarts[index]  # will raise IndexError here

    def create_restart(self, restart_number, frame_number):
        restart = self.restarts[restart_number]
        parent = restart.get_restart(frame_number)
        index = len(self.restarts)
        new_restart = Restart(index, parent, frame_number)
        self.restarts.append(new_restart)
        return new_restart

    def get_summary(self):
        # Return list of tuples for use in checkpoint tree. Each tuple in in form (parent restart number, start frame, restart number, last frame)
        restarts = [(-1, 0, 0, self.emulator_start.end_frame)]
        for r in self.restarts[1:]:
            restarts.append((r.parent.restart_number, r.start_frame, r.restart_number, r.end_frame))
        return restarts


class Restart(Serializable):
    name = None

    serializable_attributes = ['frame_history']
    serializable_computed = {'frame_history'}

    def __init__(self, restart_number, parent, start_frame=0):
        self.restart_number = restart_number
        self.parent = parent
        self.start_frame = start_frame
        self.end_frame = start_frame
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
        return self.end_frame

    # def __iter__(self):
    #     keys = sorted(self.frame_history.keys())
    #     for k in keys:
    #         yield self.frame_history[k]

    def keys(self):
        return sorted(self.frame_history.keys())

    def is_memorable(self, frame_number):
        # return frame_number % 10 == 0
        return True

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
        self.end_frame = frame_number

    ##### Retrieval

    def __getitem__(self, index):
        try:
            index = int(index)
        except TypeError:
            try:
                return [self.get_frame(i) for i in index]
            except TypeError:
                raise TypeError("argument must be a slice or an integer")
        else:
            if index < 0:
                index += len( self )
            return self.get_frame(index)  # will raise IndexError here

    def get_restart(self, frame_number):
        frame_number = int(frame_number)
        if frame_number < self.start_frame:
            parent = self.parent
            if parent is None:
                raise IndexError("Initial start of emulator has no parent")
            else:
                restart = parent.get_restart(frame_number)
        else:
            restart = self
        return restart

    def get_frame(self, frame_number):
        parent = self.get_restart(frame_number)  # could raise IndexError
        frame_number = int(frame_number)
        return self.frame_history[frame_number]

    ##### Compact

    def decimate(self):
        """Remove old history items according to an algorithm that discards
        some portion of the older history as time goes on
        """
        pass
