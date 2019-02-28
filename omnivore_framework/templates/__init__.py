import os
import glob
import json

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)

template_subdirs = [""]


def construct_path(template_dir, name):
    name = name.lstrip("/")
    if not os.path.isabs(template_dir):
        # resource path will point to the omnivore/templates directory
        path = get_resource_path(1)
        log.debug("resource path: %s" % path)
        pathname = os.path.normpath(os.path.join(path, template_dir, name))
    else:
        path = os.path.dirname(__file__)
        pathname = os.path.normpath(os.path.join(path, template_dir, name))
    return pathname


def find_template_path(name):
    log.debug(f"searching subdirs {template_subdirs}")
    if name.startswith("/"):
        log.debug(f"found absolute path to template: {name}")
        return name
    checked = []
    for toplevel in template_subdirs:
        pathname = construct_path(toplevel, name)
        log.debug("Checking for template at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found template for %s: %s" % (name, pathname))
            return pathname
        checked.append(os.path.abspath(os.path.dirname(pathname)))
    else:
        raise OSError("No template found for %s in %s" % (name, str(checked)))


def get_template_fh(name):
    # resource path will point to the omnivore/templates directory
    pathname = find_template_path(name)
    log.debug("Loading template for %s: %s" % (name, pathname))
    fh = open(pathname, "rb")
    return fh


def get_template(name):
    # resource path will point to the omnivore/templates directory
    fh = get_template_fh(name)
    source = fh.read()
    return source


class TemplateItem(dict):
    def __init__(self, json_dict):
        dict.__init__(self)
        for k, v in json_dict.items():
            self[k] = v
            setattr(self, k, v)

    def __str__(self):
        return self.get("label", "") or self.get("description", "") or self.get("name", "") or self.get("uri", "") or dict.__str__(self)

    def __lt__(self, other):
        return str(self) < str(other)

def iter_templates(inf_type=None):
    """Returns dictionary containing info about specific template types

    Dict contains keys:

    * pathname  - the full pathname to the template to differentiate default
      and user templates with the same name
    * uri
    * task  - editor name
    """
    templates = {}
    for toplevel in template_subdirs:
        pathname = construct_path(toplevel, "*")
        for template in glob.glob(pathname):
            if template.endswith(".inf"):
                # skip loading inf files
                continue
            inf = template + ".inf"
            j = None
            if os.path.exists(template) and os.path.isfile(template):
                if os.path.exists(inf):
                    try:
                        log.debug("Loading json file %s" % inf)
                        with open(inf, "r") as fh:
                            j = json.loads(fh.read())
                    except ValueError:
                        j = {}
                    if inf_type and "type" in j and j["type"] != inf_type:
                        continue
                    j["pathname"] = template
                    j["uri"] = "template://" + template
                    if "task" in j and j["task"] == "hex_edit":
                        j["task"] = "byte_edit"
                else:
                    _, ext = os.path.splitext(template)
                    if ext and ext[1:] == inf_type:
                        j = {}
                        j["pathname"] = template
                        j["uri"] = "template://" + template
                if j is not None:
                    item = TemplateItem(j)
                    log.debug(f"template: {item}")
                    yield item
