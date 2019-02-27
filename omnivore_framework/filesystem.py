import os
import sys
import datetime
from io import BytesIO, StringIO

import wx
import numpy as np

from .templates import find_template_path

import logging
log = logging.getLogger(__name__)


about = {
}

image_paths = []


def open_about(path, mode):
    try:
        value = about[path]
    except KeyError:
        raise FileNotFoundError(f"No such file in about filesytem: '{path}'")
    else:
        if mode == 'r':
            return StringIO(value.decode('utf-8'))
        elif mode == 'rb':
            return BytesIO(value)
        else:
            raise ValueError(f"invalid mode for about filesystem: '{mode}'")

def open_blank(path, mode):
    try:
        size = int(path)
    except ValueError:
        raise FileNotFoundError(f"Invalid size for blank filesytem: '{path}'")
    else:
        if mode == 'r':
            return StringIO(' ' * size)
        elif mode == 'rb':
            return BytesIO(b'\0' * size)
        else:
            raise ValueError(f"invalid mode for blank filesystem: '{mode}'")

def open_template(path, mode):
    try:
        real_path = find_template_path(path)
    except OSError as e:
        raise FileNotFoundError(str(e))
    else:
        return open(real_path, mode)

def open_icon(path, mode):
    try:
        real_path = find_image_path(path)
    except OSError as e:
        raise FileNotFoundError(str(e))
    else:
        return open(real_path, mode)

filesystems = {
    "about://": open_about,
    "blank://": open_blank,
    "template://": open_template,
    "icon://": open_icon,
}

def fsopen(uri, mode):
    for prefix, opener in filesystems.items():
        if uri.startswith(prefix):
            return opener(uri[len(prefix):], mode)
    return open(uri, mode)


class WxIconFileSystemHandler(wx.FileSystemHandler):
    def CanOpen(self, location):
        return self.GetProtocol(location) == "icon"

    def OpenFile(self, fs, location):
        # For some reason, the actual path shows up as the right location
        # rather than left, and it includes the leading slashes.
        path = self.GetRightLocation(location).lstrip("/")
        wxfs = wx.FileSystem()
        fsfile = wxfs.OpenFile("memory:%s" % path)
        if fsfile is None:
            try:
                fh = fsopen(location, "rb")
            except FileNotFoundError as e:
                log.error(str(e))
                return None
            data = np.fromstring(fh.read(), dtype=np.uint8)
            log.debug("Created %s in wxMemoryFS" % path)
            wx.MemoryFSHandler.AddFileWithMimeType(path, data, "image/png")

            fsfile = wxfs.OpenFile("memory:%s" % path)
        else:
            log.debug("Found %s in wxMemoryFS" % path)
        return fsfile


def init_filesystems(app):
    wx.FileSystem.AddHandler(WxIconFileSystemHandler())
    wx.FileSystem.AddHandler(wx.MemoryFSHandler())

    global about
    about['app'] = app.about_html.encode('utf-8')

    global image_paths
    path = get_image_path("icons")
    if path not in image_paths:
        image_paths.append(path)


def find_image_path(name):
    log.debug(f"searching subdirs {image_paths}")
    checked = []
    for toplevel in image_paths:
        path = os.path.join(toplevel, name)
        log.debug("Checking for image at %s" % path)
        if os.path.exists(path):
            log.debug("Found image for %s: %s" % (name, path))
            return path
        checked.append(toplevel)
    else:
        raise OSError("No image found for %s in %s" % (name, str(checked)))


def get_image_path(rel_path, module=None, file=None, up_one_level=False, excludes=[]):
    """Get the image path for static images relative to the specified module
    or file.
    
    The image path will be modified to find images in py2exe/py2app
    locations assuming that the data files have been added using the above
    get_py2exe_data_files function.
    
    Either the module or file keyword parameter may be specified to provide
    a relative module or file name.  The module may be specified either by
    reference to an imported module, or by a dotted string.  The file must be
    specified using the __file__ keyword.  If both are specified, file takes
    precedence.
    
    For example, in omnivore, the images are located in a directory "icons" in
    main omnivore_framework directory (e.g. omnivore_framework/icons):
        
    import omnivore_framework
    image_path = get_image_path("icons", omnivore_framework)
    
    will return the absolute path of "omnivore/icons".
    
    An example using the file keyword: if the current module is in the
    omnivore_framework/framework directory, then the call to:
    
    get_image_path("icons", file=__file__)
    
    will contain the absolute path to the omnivore_framework/framework/icons directory.
    """
    if file is None:
        if module is None:
            path = __file__
        else:
            try:
                path = module.__file__
            except AttributeError:
                # must be a string containing the module hiearchy
                path = module.replace(".", "/") + "/this-will-be-removed.py"
    else:
        path = file.replace(".", "/")
    import os
    import sys
    if up_one_level:
        path = os.path.dirname(path)
    log.debug("get_image_path: file=%s, path=%s, module=%s" % (file, path, module))
    frozen = getattr(sys, 'frozen', False)
    image_path = os.path.normpath(os.path.join(os.path.dirname(path), rel_path))
    if frozen:
        if frozen == True:
            # pyinstaller sets frozen=True and uses sys._MEIPASS
            root = sys._MEIPASS
            image_path = os.path.normpath(os.path.join(root, image_path))
        elif frozen in ('macosx_app'):
            #print "FROZEN!!! %s" % frozen
            root = os.environ['RESOURCEPATH']
            if ".zip/" in image_path:
                zippath, image_path = image_path.split(".zip/")
            image_path = os.path.normpath(os.path.join(root, image_path))
        else:
            log.error("App packager %s not yet supported for image paths!!!")
    elif not os.path.isabs(path):
        if "/" in path:
            toplevel, modulepath = path.split("/", 1)
            modulepath = os.path.dirname(modulepath)
        elif "\\" in path:
            toplevel, modulepath = path.split("\\", 1)
            modulepath = os.path.dirname(modulepath)
        else:
            toplevel = path
            modulepath = ""
        path = os.path.dirname(sys.modules[toplevel].__file__)
        rel_path = os.path.join(modulepath, rel_path)
        log.debug("get_image_path: relative! path=%s toplevel=%s modulepath=%s rel_path=%s" % (path, toplevel, modulepath, rel_path))
        image_path = os.path.normpath(os.path.join(path, rel_path))
    log.debug("get_image_path: image_path=%s" % image_path)
    return image_path
