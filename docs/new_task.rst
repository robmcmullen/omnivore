====================
Creating a New Task
====================

FontEditor: Modifying an Existing Task
======================================

duplicate directory:

```
cd omnivore8bit
cp -pr map_edit font_edit
cd font_edit
rm *.pyc # remove old compiled files so python doesn't see files that are renamed
mv map_editor.py font_editor.py
chpat.py map_edit font_edit *.py
chpat.py MapEdit FontEdit *.py
```

* Edit docstring in task.py to reflect the new mode's function

