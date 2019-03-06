import os

from .. import filesystem
from .. import errors

import logging
log = logging.getLogger(__name__)


def get_htmlhelp(name):
    attempts = []
    for subdir in filesystem.help_paths:
        pathname = os.path.normpath(os.path.join(subdir, name))
        log.debug("Checking for htmlhelp at %s" % pathname)
        if os.path.exists(pathname):
            log.debug("Found htmlhelp for %s: %s" % (name, pathname))
            return pathname
        attempts.append(pathname)
    else:
        log.debug("No htmlhelp found for %s in %s" % (name, attempts))
        raise errors.MissingDocumentationError("Unable to locate %s help files; installation error?\nThe files should be in one of the following:\n%s\n\nbut were not found." % (name, "\n  * " + "\n  * ".join([os.path.dirname(d) for d in attempts])))
