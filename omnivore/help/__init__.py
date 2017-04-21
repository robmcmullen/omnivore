import os

from traits.trait_base import get_resource_path

import logging
log = logging.getLogger(__name__)


class MissingDocumentationError(RuntimeError):
    pass


root_resource_path = None

help_dirs = ["omnivore/help", "omnivore8bit/help"]


def get_htmlhelp(name):
    global root_resource_path

    # resource path will point to the omnivore/templates directory
    if root_resource_path is None:
        path = get_resource_path(1)
        root_resource_path = os.path.normpath(os.path.join(path, "../.."))
        log.debug("resource path: %s" % root_resource_path)
    attempts = []
    for subdir in help_dirs:
        pathname = os.path.normpath(os.path.join(root_resource_path, subdir, name))
        log.debug("Checking for htmlhelp at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found htmlhelp for %s: %s" % (name, pathname))
            return pathname
        attempts.append(pathname)
    else:
        log.debug("No htmlhelp found for %s in %s" % (name, attempts))
        raise MissingDocumentationError("Unable to locate %s help files; installation error?\nThe files should be in one of the following:\n%s\n\nbut were not found." % (name, "\n  * " + "\n  * ".join([os.path.dirname(d) for d in attempts])))
