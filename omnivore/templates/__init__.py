import os

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


def get_template(name):
    # resource path will point to the omnivore/templates directory
    path = get_resource_path(1)
    log.debug("resource path: %s" % path)
    for toplevel in ["", "../../omnivore8bit/templates"]:
        pathname = os.path.normpath(os.path.join(path, toplevel, name))
        log.debug("Checking for template at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Loading template for %s: %s" % (name, pathname))
            with open(pathname, "rb") as fh:
                source = fh.read()
            return source
    else:
        log.debug("No template found for %s in %s" % (name, path))
