import os

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


class MissingDocumentationError(RuntimeError):
    pass


def get_htmlhelp(name):
    # resource path will point to the omnivore/templates directory
    path = get_resource_path(1)
    log.debug("resource path: %s" % path)
    attempts = []
    for toplevel in ["", "../../omnivore8bit/help"]:
        pathname = os.path.normpath(os.path.join(path, toplevel, name))
        log.debug("Checking for htmlhelp at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found htmlhelp for %s: %s" % (name, pathname))
            return pathname
        attempts.append(pathname)
    else:
        log.debug("No htmlhelp found for %s in %s" % (name, path))
        raise MissingDocumentationError("Unable to locate %s help files; installation error?\nThe files should be in one of the following:\n%s\n\nbut were not found." % (name, "\n  * " + "\n  * ".join([os.path.dirname(d) for d in attempts])))
