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
    def __init__(self, keyword, inf_type, json_dict):
        dict.__init__(self)
        self.keyword = keyword
        self.inf_type = inf_type
        for k, v in json_dict.items():
            self[k] = v
            setattr(self, k, v)

    def __str__(self):
        return self.get("label", "") or self.get("description", "") or self.get("name", "") or self.keyword

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
        wildcard = construct_path(toplevel, "*")
        for template_path in glob.glob(wildcard):
            if template_path.endswith(".inf"):
                # skip loading inf files
                continue
            inf_path = template_path + ".inf"
            j = None
            if os.path.exists(template_path) and os.path.isfile(template_path):
                keyword = os.path.basename(template_path)
                keyword2, ext = os.path.splitext(keyword)
                if ext and ext[1:] == inf_type:
                    keyword = keyword2
                    ext = inf_type
                if os.path.exists(inf_path):
                    try:
                        log.debug("Loading json file %s" % inf_path)
                        with open(inf_path, "r") as fh:
                            j = json.loads(fh.read())
                    except ValueError as e:
                        log.debug(f"Error in json: {e}")
                        j = {}
                    if inf_type and "type" in j and j["type"] != inf_type:
                        continue
                    j["pathname"] = template_path
                    j["uri"] = "template://" + template_path
                    if "task" in j and j["task"] == "hex_edit":
                        j["task"] = "byte_edit"
                elif ext == inf_type:
                    j = {}
                    j["type"] = inf_type
                    j["pathname"] = template_path
                    j["uri"] = "template://" + template_path
                if j is not None:
                    item = TemplateItem(keyword, inf_type, j)
                    log.debug(f"template: {item}")
                    yield item
