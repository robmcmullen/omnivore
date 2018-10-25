import os
import sys
import time

from datetime import datetime
import fs
import wx

from .document import BaseDocument

import logging
log = logging.getLogger(__name__)


def guess_document(guess):
    app = wx.GetApp().tasks_application
    service = app.get_service("omnivore_framework.file_type.i_file_recognizer.IFileRecognizerDriver")
    log.debug("SERVICE!!! %s" % service)

    # Attempt to classify the guess using the file recognizer service
    document = service.recognize(guess)
    log.debug("created document %s (mime=%s)" % (document, document.metadata.mime))
    return document

def load_file(uri, active_task=None, task_id="", in_current_window=False, **kwargs):
    app = wx.GetApp().tasks_application
    log.debug("load_file: uri=%s task_id=%s" % (uri, task_id))
    from ..utils.file_guess import FileGuess
    # The FileGuess loads the first part of the file and tries to identify it.
    try:
        guess = FileGuess(uri)
    except fs.errors.FSError as e:
        log.error("File load error: %s" % str(e))
        if active_task is not None:
            active_task.window.error(str(e), "File Load Error")
        return

    if len(guess.raw_bytes) == 0:
        if active_task is not None:
            active_task.window.error("Zero length file!\nUnable to determine file type.", "File Load Error")
        return

    # Attempt to classify the guess using the file recognizer service
    document = guess_document(guess)
    log.debug("using %s for %s" % (document.__class__.__name__, guess.metadata.uri))
    if document.load_error:
        if app.active_window:
            app.active_window.warning(document.load_error, "Document Load Error")

    # Short circuit: if the file can be edited by the active task, use that!
    if active_task is not None and active_task.can_edit(document):
        log.debug("active task %s can edit %s" % (active_task, document))
        active_task.new(document, **kwargs)
        return

    possibilities = get_possible_task_factories(document, task_id)
    if not possibilities:
        log.debug("no editor for %s" % uri)
        return
    best = find_best_task_factory(document, possibilities)
    log.debug("best task match: %s" % best.id)

    if active_task is not None:
        # Ask the active task if it's OK to load a different editor
        if not active_task.allow_different_task(guess, best.factory):
            return
        dummy = app.document_class(metadata="application/octet-stream")
        if active_task.can_edit(document) and active_task.ask_attempt_loading_as_octet_stream(guess, best.factory):
            log.debug("Active task %s allows application/octet-stream" % active_task.id)
            active_task.new(document, **kwargs)
            return
        if in_current_window:
            task = create_task_in_window(best.id, active_task.window)
            task.new(document, **kwargs)
            return

    # Look for existing task in current windows
    task = find_active_task_of_type(best.id)
    if task:
        log.debug("Found task %s in current window" % best.id)
        task.new(document, **kwargs)
        return

    log.debug("Creating task %s in current window" % best.id)
    create_task_from_factory_id(document, best.id, **kwargs)

def get_possible_task_factories(document, task_id=""):
    app = wx.GetApp().tasks_application
    possibilities = []
    for factory in app.task_factories:
        log.debug("checking factory: %s=%s for %s" % (factory.id, factory.name, task_id))
        if task_id:
            if factory.id == task_id or factory.factory.editor_id == task_id:
                possibilities.append(factory)
        elif hasattr(factory.factory, "can_edit"):
            if factory.factory.can_edit(document):
                log.debug("  can edit: %s" % document)
                possibilities.append(factory)
    log.debug("get_possible_task_factories: %s" % str([(p.name, p.id) for p in possibilities]))
    return possibilities

def find_best_task_factory(document, factories):
    scores = []
    for factory in factories:
        log.debug("factory: %s=%s" % (factory.id, factory.name))
        if document.last_task_id == factory.id or document.last_task_id == factory.factory.editor_id:
            # short circuit if document is requesting a specific task
            return factory
        score = factory.factory.get_match_score(document)
        scores.append((score, factory))
    scores.sort()
    log.debug("find_best_task_factory: %s" % str([(s, p.name, p.id) for (s, p) in scores]))
    return scores[-1][1]

def get_task_factory(task_id):
    app = wx.GetApp().tasks_application
    for factory in app.task_factories:
        if factory.id == task_id or factory.factory.editor_id == task_id:
            return factory
    return None

def find_best_task_id(task_id):
    app = wx.GetApp().tasks_application
    if task_id:
        for factory in app.task_factories:
            if factory.id == task_id or ".%s." % task_id in factory.id or ".%s" % task_id in factory.id:
                return factory.id
    return ""  # empty string will result in scanning the file for the best match

def create_task_from_factory_id(guess, factory_id, **kwargs):
    app = wx.GetApp().tasks_application
    window = app.active_window
    log.debug("  window=%s" % str(window))
    for task in window.tasks:
        if task.id == factory_id:
            break
    else:
        task = app.create_task(factory_id)
    add_task_to_window(window, task)
    task.new(guess, **kwargs)
    return task

def create_task_in_window(task_id, window):
    app = wx.GetApp().tasks_application
    log.debug("creating %s task" % task_id)
    task = app.create_task(task_id)
    add_task_to_window(window, task)
    return task

def add_task_to_window(window, task):
    app = wx.GetApp().tasks_application
    window.add_task(task)
    window.activate_task(task)
    app.restore_perspective(window, task)

def find_active_task_of_type(task_id):

    app = wx.GetApp().tasks_application
    # Until remove_task bug is fixed, don't create any new windows, just
    # add a new task to the current window unless the task already exists
    w = list(app.windows)
    if not w:
        # OS X might not have any windows open; a menubar is allowed to
        # exist without windows.
        return None
    try:
        i = w.index(app.active_window)
        w[0:0] = [app.active_window]
        w.pop(i)
    except ValueError:
        pass

    for window in w:
        for t in window.tasks:
            if t.id == task_id:
                log.debug("found non-active task in current window; activating!")
                window.activate_task(t)
                return t
    if window:
        task = create_task_in_window(task_id, window)
        return task
#        # Check active window first, then other windows
#        w = list(app.windows)
#        try:
#            i = w.index(app.active_window)
#            w[0:0] = [app.active_window]
#            w.pop(i)
#        except ValueError:
#            pass
#
#        for window in w:
#            log.debug("window: %s" % window)
#            log.debug("  active task: %s" % window.active_task)
#            if window.active_task.id == task_id:
#                log.debug("  found active task")
#                return window.active_task
#        log.debug("  no active task matches %s" % task_id)
#        for window in w:
#            task = window.active_task
#            if task is None:
#                continue
#            # if no editors in the task, replace the task with the new task
#            log.debug("  window %s: %d" % (window, len(task.editor_area.editors)))
#            if len(task.editor_area.editors) == 0:
#                log.debug("  replacing unused task!")
#                # The bugs in remove_task seem to have been fixed so that the
#                # subsequent adding of a new task does seem to work now.  But
#                # I'm leaving in the workaround for now of simply closing the
#                # active window, forcing the new task to open in a new window.
#                if True:
#                    log.debug("removing task %s" % task)
#                    print window
#                    #window.remove_task(task)
#                    task = app.create_task_in_window(task_id, window)
#                    return task
#                else:
#                    window.close()
#                    return None

def find_or_create_task_of_type(task_id):
    app = wx.GetApp().tasks_application
    task = find_active_task_of_type(task_id)
    if not task:
        log.debug("task %s not found in active windows; creating new window" % task_id)
        window = app.create_window()
        task = create_task_in_window(task_id, window)
        window.open()
    return task
