import os

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


def find_template_path(name):
    # resource path will point to the omnivore/templates directory
    path = get_resource_path(1)
    log.debug("resource path: %s" % path)
    name = name.lstrip("/")
    for toplevel in ["", "../../omnivore8bit/templates"]:
        pathname = os.path.normpath(os.path.join(path, toplevel, name))
        log.debug("Checking for template at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found template for %s: %s" % (name, pathname))
            return pathname
    else:
        raise OSError("No template found for %s in %s" % (name, path))


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
