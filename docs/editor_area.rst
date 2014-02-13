===========
Editor Area
===========

The editor area (IEditorArea/MEditorArea) is a container for tabbed editors.

pyface/pyface/tasks/i_editor_area_pane.py

* How is a factory defined? From the source code docs:

        The 'factory' parameter is a callabe of form:
            callable(editor_area=editor_area, obj=obj) -> IEditor
        Often, factory will be a class that implements the 'IEditor' interface.

        The 'filter' parameter is a callable of form:
            callable(obj) -> bool
        that indicates whether the editor factory is suitable for an object.
