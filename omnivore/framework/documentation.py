import os
import sys

from omnivore.utils.textutil import slugify

import logging
log = logging.getLogger(__name__)

class OmnivoreDocumentationError(RuntimeError):
    pass

class AlreadySeenError(OmnivoreDocumentationError):
    pass

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


rst_toc_entry_template = "   {0}"

rst_toc_of_subdir_template = "   {0}/index"

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


class RSTDocs(object):
    default_templates = {
        "manual_index": """
.. _{slug}

{title}

Introduction
============

{intro}

Editors
=======

.. toctree::
   :maxdepth: 2

{toc}
""",

        "task_index":"""
.. _{slug}

{title}

Overview
========

{overview}

Menus
=====

.. toctree::
   :maxdepth: 2

{toc}
""",

        "page": """
.. _{slug}

{title}

""",
    }


    def __init__(self, title, directory):
        self.title = title
        self.title_slug = slugify(title)
        self.directory = directory
        self.template_dir = directory
        self.template_suffix = ".rst.in"
        self.sections = []

    def get_subdir(self, name):
        subdir = os.path.join(self.directory, name)
        try:
            os.mkdir(subdir)
        except OSError, e:
            # directory exists!
            pass
        return subdir

    def get_template(self, kind):
        filename = os.path.join(self.template_dir, kind + self.template_suffix)
        try:
            with open(filename, "r") as fh:
                template = fh.read()
        except IOError, e:
            template = self.default_templates[kind]
        return template

    def get_action_text(self, action, menu, summaries_seen):
        doc_hint = getattr(action, "doc_hint", "")
        if doc_hint == "summary":
            summary_id = "/".join(menu) + "/" + action.__class__.__name__
            if summary_id in summaries_seen:
                raise AlreadySeenError
            summaries_seen.add(summary_id)
        text = get_best_doc(action)
        return text, doc_hint

    def create_task_sections(self, directory, hierarchy, base_slug):
        toc_entries = []
        pages = []
        current_page = []
        summaries_seen = set()
        template = self.get_template("page")
        for path, action in hierarchy:
            menu, title, level, is_action = split_path(path)
            if level > 1:
                if not is_action:  # explicit menu
                    if level == 2:  # toplevel menu item
                        slug = "%s.%s" % (base_slug, slugify(title))
                        toc_entries.append((slug, title))
                        subs = {
                            "slug": slug,
                            "title": get_rst_section_title(level, title, True),
                        }
                        current_page = [template.format(**subs)]
                        print "New page for %s: %s" % (title, slug)
                        log.debug("New page for %s: %s" % (title, slug))
                        pages.append((slug, title, current_page))
                    else:
                        log.debug("Submenu %s")
                        current_page.append(get_rst_section_title(level - 1, title))

                else:  # menu item could be in a submenu or up a level
                    try:
                        text, doc_hint = self.get_action_text(action, menu, summaries_seen)
                    except AlreadySeenError:
                        continue
                    current_page.extend(get_rst_action_description(level, title, text, doc_hint))

        for slug, title, page in pages:
            text = "\n".join(page) + "\n"
            filename = os.path.join(directory, "%s.rst" % slug)
            log.debug("Writing %s" % filename)
            with open(filename, "w") as fh:
                fh.write(text)

        return toc_entries

    def add_task(self, task):
        doc_hint = getattr(task, "doc_hint", "")
        if doc_hint == "skip":
            log.debug("Skipping documentation for task %s" % task.editor_id)
            return

        hierarchy = task.get_menu_action_hierarchy()
        slug = task.editor_id

        subdir = self.get_subdir(slug)
        toc_entries = self.create_task_sections(subdir, hierarchy, task.editor_id)
        template = self.get_template("task_index")

        subs = {
            "slug": slug,
            "title": get_rst_section_title(2, task.name, True),
            "toc": "\n".join([rst_toc_entry_template.format(*t) for t in toc_entries]),
            "overview": task.__doc__,
        }

        text = template.format(**subs)
        filename = os.path.join(subdir, "index.rst")
        log.debug("Writing %s" % filename)
        with open(filename, "w") as fh:
            fh.write(text)

        self.sections.append((task.editor_id, task.name))

    def create_manual(self, intro=""):
        template = self.get_template("manual_index")

        subs = {
            "slug": self.title_slug,
            "title": get_rst_section_title(2, self.title, True),
            "toc": "\n".join([rst_toc_of_subdir_template.format(*t) for t in self.sections]),
            "intro": intro,
        }

        text = template.format(**subs)

        print "New manual index %s: %s" % (self.title, self.title_slug)
        log.debug("Writing index.rst")
        with open(os.path.join(self.directory, "index.rst"), "w") as fh:
            fh.write(text)
