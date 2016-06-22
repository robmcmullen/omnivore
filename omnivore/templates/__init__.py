import os

from traits.trait_base import get_resource_path

def get_template(name):
    path = get_resource_path(1)
    print path, name
    pathname = os.path.normpath("%s/%s" % (path, name))
    if os.path.exists(pathname):
        with open(pathname, "rb") as fh:
            source = fh.read()
        return source
