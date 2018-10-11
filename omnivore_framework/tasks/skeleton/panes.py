"""Sample panes for Skeleton

"""
# Enthought library imports.
from pyface.tasks.api import DockPane


class SkeletonPane1(DockPane):
    #### TaskPane interface ###################################################

    id = 'text_edit.pane1'
    name = 'Skeleton Pane 1'


class SkeletonPane2(DockPane):
    #### TaskPane interface ###################################################

    id = 'text_edit.pane2'
    name = 'Skeleton Pane 2'


class SkeletonPane3(DockPane):
    #### TaskPane interface ###################################################

    id = 'text_edit.pane3'
    name = 'Skeleton Pane 3'
