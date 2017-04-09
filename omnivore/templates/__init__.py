import os

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


def get_template(name):
    path = get_resource_path(1)
    pathname = os.path.normpath("%s/%s" % (path, name))
    if os.path.exists(pathname):
        log.debug("Loading template for %s: %s" % (name, pathname))
        with open(pathname, "rb") as fh:
            source = fh.read()
        return source
    else:
        log.debug("No template found for %s in %s" % (name, path))
