import os
import sys

from omnivore.utils.textutil import slugify

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

def trim(docstring):
    # docstring formatter from PEP-257
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def get_best_doc(action):
    if action.__doc__:
        return trim(action.__doc__)
    else:
        return action.description or action.tooltip

rst_task_index_template = """
.. _{slug}

{title}

Menus
=====

.. toctree::
   :maxdepth: 2
"""

rst_toc_entry_template = "   {0}"

rst_toc_of_subdir_template = "   {0}/index"

rst_page_template = """
.. _{slug}

{title}

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

def get_rst_action_description(level, title, text, doc_hint):
    lines = []
    indent = ""
    if doc_hint == "summary":
        # just use text as is because the menu title will have already been
        # printed
        level = -1
    if level < 0:
        # do nothing, format text as is
        pass
    elif level == 2:  # Actions in the main pulldown are subsections
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

def create_task_rst(directory, task):
    hierarchy = task.get_menu_action_hierarchy()
    subdir = os.path.join(directory, task.editor_id)
    try:
        os.mkdir(subdir)
    except OSError, e:
        # directory exists!
        pass
    toc_entries = create_multi_rst(subdir, hierarchy, lambda a: "%s.%s" % (task.editor_id, slugify(a)))
    lines = [rst_task_index_template.format(slug=task.editor_id, title=get_rst_section_title(2, task.name, True))]
    lines.extend([rst_toc_entry_template.format(*t) for t in toc_entries])

    text = "\n".join(lines) + "\n"
    filename = os.path.join(subdir, "index.rst")
    log.debug("Writing %s" % filename)
    with open(filename, "w") as fh:
        fh.write(text)

    return task.editor_id, task.name

def create_multi_rst(directory, hierarchy, _slugify=slugify):
    toc_entries = []
    pages = []
    current_page = []
    summaries_seen = set()
    for path, action in hierarchy:
        menu, title, level, is_action = split_path(path)
        if level > 1:
            if not is_action:  # explicit menu
                if level == 2:  # toplevel menu item
                    slug = _slugify(title)
                    toc_entries.append((slug, title))
                    current_page = [rst_page_template.format(slug=slug, title=get_rst_section_title(level, title, True))]
                    print "New page for %s" % title, id(current_page)
                    log.debug("New page for %s" % title)
                    pages.append((slug, title, current_page))
                else:
                    log.debug("Submenu %s")
                    current_page.append(get_rst_section_title(level - 1, title))

            else:  # menu item could be in a submenu or up a level
                doc_hint = getattr(action, "doc_hint", "")
                if doc_hint == "summary":
                    summary_id = "/".join(menu) + "/" + action.__class__.__name__
                    print "SUMMARY: ", level, summary_id, summary_id in summaries_seen
                    if summary_id in summaries_seen:
                        continue
                    summaries_seen.add(summary_id)
                text = get_best_doc(action)
                current_page.extend(get_rst_action_description(level, title, text, doc_hint))

    for slug, title, page in pages:
        text = "\n".join(page) + "\n"
        filename = os.path.join(directory, "%s.rst" % slug)
        log.debug("Writing %s" % filename)
        with open(filename, "w") as fh:
            fh.write(text)

    return toc_entries

def create_manual_index_rst(directory, sections, title):
    lines = [rst_task_index_template.format(slug=slugify(title), title=get_rst_section_title(2, title, True))]
    lines.extend([rst_toc_of_subdir_template.format(*t) for t in sections])

    text = "\n".join(lines) + "\n"
    log.debug("Writing index.rst")
    with open(os.path.join(directory, "index.rst"), "w") as fh:
        fh.write(text)
