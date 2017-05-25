import os
import glob
import json

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


relative_template_subdirs = ["", "../../omnivore8bit/templates"]


def construct_path(subdir, name):
    # resource path will point to the omnivore/templates directory
    path = get_resource_path(1)
    log.debug("resource path: %s" % path)
    name = name.lstrip("/")
    pathname = os.path.normpath(os.path.join(path, subdir, name))
    return pathname


def find_template_path(name):
    checked = []
    for toplevel in relative_template_subdirs:
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


def iter_templates():
    for toplevel in relative_template_subdirs:
        pathname = construct_path(toplevel, "*")
        for template in glob.glob(pathname):
            inf = template + ".inf"
            if os.path.exists(template) and os.path.isfile(template) and os.path.exists(inf):
                try:
                    with open(inf, "r") as fh:
                        j = json.loads(fh.read())
                        print "json:", j
                except ValueError:
                    j = {}
                    raise
                j["pathname"] = template
                j["uri"] = "template://" + os.path.basename(template)
                log.debug("template json: %s" % str(template))
                yield j
