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
    if name.startswith("/"):
        return name
    checked = []
    for toplevel in template_subdirs:
        pathname = construct_path(toplevel, name)
        log.debug("Checking for template at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found template for %s: %s" % (name, pathname))
            return pathname
        checked.append(os.path.abspath(toplevel))
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


def iter_templates(inf_type=None):
    templates = {}
    for toplevel in template_subdirs:
        pathname = construct_path(toplevel, "*")
        for template in glob.glob(pathname):
            inf = template + ".inf"
            if os.path.exists(template) and os.path.isfile(template) and os.path.exists(inf):
                try:
                    log.debug("Loading json file %s" % inf)
                    with open(inf, "r") as fh:
                        j = json.loads(fh.read())
                except ValueError:
                    j = {}
                if inf_type and j["type"] != inf_type:
                    continue
                j["pathname"] = template
                # Allow full path in template to differentiate default and user
                # templates with the same name
                j["uri"] = "template://" + template
                if "task" in j and j["task"] == "hex_edit":
                    j["task"] = "byte_edit"
                log.debug("template json: %s" % str(template))
                yield j
