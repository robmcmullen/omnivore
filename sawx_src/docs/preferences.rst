===========
Preferences
===========

The default style of tasks preferences is a tabbed window where each pane has a header and then its preferences below. I kind of like the peppy style with tabs and a list where each pane has its own entry in the last.

Preferences seem to be controlled by envisage/envisage/ui/tasks/preferences_dialog.py

It calls a traits editor ListEditor to display the body of the dialog.

The toolkit specific stuff seems to be in: apptools/apptools/preferences/ui.  Maybe?


The workbench plugin uses PreferencePages as in:

http://docs.enthought.com/envisage/envisage_core_documentation/preferences.html

