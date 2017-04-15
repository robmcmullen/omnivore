import os
import sys

import logging
log = logging.getLogger(__name__)

# The hierarchy coming from task.get_menu_action_hierarchy() is a list of
# tuples that look like this:
#
# ("Menubar -> ", None)
# ("Menubar -> File -> ", None)
# ("Menubar -> File -> New -> ", None)
# ("Menubar -> File -> New -> Bitmap File", <omnivore.framework.actions.NewFileAction object at 0x7f28ceeaad10>)
# ("Menubar -> File -> New -> Bitmap Image", <omnivore.framework.actions.NewFileAction object at 0x7f28cee8bfb0>)
# ("Menubar -> File -> New -> Text File", <omnivore.framework.actions.NewFileAction object at 0x7f28cee8be30>)
# ("Menubar -> File -> Open...", <omnivore.framework.actions.OpenAction object at 0x7f28cf75b590>)
# ("Menubar -> File -> Open Recent -> ", None)
# ("Menubar -> File -> Open Recent -> about://omnivore", <omnivore.plugins.open_recent.OpenRecentAction object at 0x7f28ceec4830>)
# ("Menubar -> File -> Insert File...", <omnivore8bit.hex_edit.actions.InsertFileAction object at 0x7f28cf75b830>)
# ("Menubar -> File -> Save", <omnivore.framework.actions.SaveAction object at 0x7f28cf75bd70>)
# ("Menubar -> File -> Save As...", <omnivore.framework.actions.SaveAsAction object at 0x7f28cf75bdd0>)
# ("Menubar -> File -> Save Segment As -> ", None)
# ("Menubar -> File -> Save As Image...", <omnivore.framework.actions.SaveAsImageAction object at 0x7f28cf781470>)
# ("Menubar -> File -> Revert", <omnivore.framework.actions.RevertAction object at 0x7f28cf781c50>)
# ("Menubar -> File -> Page Setup...", <omnivore.framework.actions.PageSetupAction object at 0x7f28cf71c1d0>)
# ("Menubar -> File -> Print Preview", <omnivore.framework.actions.PrintPreviewAction object at 0x7f28cf71c230>)
# ("Menubar -> File -> Print...", <omnivore.framework.actions.PrintAction object at 0x7f28cf71c290>)
# ("Menubar -> File -> Export as XEX...", <omnivore8bit.hex_edit.actions.SaveAsXEXAction object at 0x7f28cf71ccb0>)
# ("Menubar -> File -> Export as Boot Disk...", <omnivore8bit.hex_edit.actions.SaveAsXEXBootAction object at 0x7f28cf71cd10>)
# ("Menubar -> File -> Quit", <omnivore.framework.actions.ExitAction object at 0x7f28cf737650>)
# ("Menubar -> Edit -> ", None)
# ("Menubar -> Edit -> Undo", <omnivore.framework.actions.UndoAction object at 0x7f28cf737950>)
# ("Menubar -> Edit -> Redo", <omnivore.framework.actions.RedoAction object at 0x7f28cf7379b0>)
# ("Menubar -> Edit -> Revert to Baseline Data", <omnivore8bit.hex_edit.actions.RevertToBaselineAction object at 0x7f28cf737cb0>)

def split_path(path):
    parts = path.split(" -> ")
    title = parts[-1]
    if title:
        menu = parts[0:-1]
        is_action = True
    else:  # skip the last one, it's blank
        title = parts[-2]
        menu = parts[0:-1]
        is_action = False
    # print "SPLIT", parts
    return menu, title, len(menu), is_action

def get_best_doc(action):
    return action.__doc__ or action.description or action.tooltip

rst_index_template = """
====
Test
====

Menus
=====

.. toctree::
   :maxdepth: 2
"""

rst_toc_template = "   %s"

rst_page_template = """
%s

"""

rst_section_chars = {
    2: "=",  # Menu items, first submenu
    3: "-",  # Submenu items, second submenu
    4: "~",
    5: "^"
}

def get_rst_section_title(level, title, page=False):
    divider = rst_section_chars[level] * len(title)
    return "\n\n%s\n%s\n%s\n\n" % (divider if page else "", title, divider)

def get_rst_action_description(level, title, text):
    lines = []
    indent = ""
    if level == 2:  # Actions in the main pulldown are subsections
        lines.append(get_rst_section_title(level, title))
    elif level == 3:  # Actions in the first submenu level
        lines.append("%s:" % title)
        indent = "    "
    else:  # Actions in deeper submenus
        lines.append("* %s:" % title)
        text = ""  # force no description
    lines.extend([indent + t for t in text.splitlines()])
    lines.append("")
    return lines

def create_multi_rst(directory, hierarchy):
    index_text = [rst_index_template]
    pages = []
    current_page = []
    for path, action in hierarchy:
        menu, title, level, is_action = split_path(path)
        if level > 1:
            if not is_action:  # explicit menu
                if level == 2:  # toplevel menu item
                    index_text.append(rst_toc_template % title)
                    current_page = [rst_page_template % get_rst_section_title(level, title, True)]
                    log.debug("New page for %s" % title)
                    pages.append((title, current_page))
                else:
                    log.debug("Submenu %s")
                    current_page.append(get_rst_section_title(level - 1, title))

            else:  # menu item could be in a submenu or up a level
                text = get_best_doc(action)
                current_page.extend(get_rst_action_description(level, title, text))

    for title, page in pages:
        text = "\n".join(page) + "\n"
        filename = os.path.join(directory, "%s.rst" % title)
        log.debug("Writing %s" % filename)
        with open(os.path.join(directory, "%s.rst" % title), "w") as fh:
            fh.write(text)

    text = "\n".join(index_text) + "\n"
    log.debug("Writing index.rst")
    with open(os.path.join(directory, "index.rst"), "w") as fh:
        fh.write(text)
