"""Sample panes for Image Editor

"""
# Enthought library imports.
from pyface.tasks.api import DockPane


class Pane1(DockPane):
    #### TaskPane interface ###################################################

    id = 'image_edit.pane1'
    name = 'Pane 1'


class Pane2(DockPane):
    #### TaskPane interface ###################################################

    id = 'image_edit.pane2'
    name = 'Pane 2'


class Pane3(DockPane):
    #### TaskPane interface ###################################################

    id = 'image_edit.pane3'
    name = 'Pane 3'
