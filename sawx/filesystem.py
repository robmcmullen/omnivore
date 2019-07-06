import os
import sys
import glob
import datetime
from io import BytesIO, StringIO

import wx
import numpy as np

import logging
log = logging.getLogger(__name__)


about = {
}

image_paths = []

# None is used as a separator between user paths and system paths. User paths
# come first and can shadow identically named system templates. So, insert user
# paths using code like ``template_paths[0:0] = ["my/cool/path"]`` and append
# system paths with ``template_paths.append("my/system/path")``
template_paths = [None]

help_paths = []



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

computed_filesystems = {
    "about://": open_about,
    "blank://": open_blank,
}


def calc_template_paths(include_user_defined):
    paths = template_paths
    if not include_user_defined:
        try:
            start_system = paths.index(None)
        except ValueError:
            pass
        else:
            paths = paths[start_system+1:]
    return paths

def find_template_path(name, include_user_defined=True):
    paths = calc_template_paths(include_user_defined)
    return find_first_in_paths(paths, name)

def find_latest_template_path(name, include_user_defined=True):
    paths = calc_template_paths(include_user_defined)
    return find_latest_in_paths(paths, name)

def find_image_path(name):
    return find_first_in_paths(image_paths, name)

filesystems_to_local_file = {
    "template://": find_template_path,
    "icon://": find_image_path,
    "file://": lambda path: path,
}

def filesystem_path(uri):
    for prefix, path_finder in filesystems_to_local_file.items():
        if uri.startswith(prefix):
            try:
                local_path = path_finder(uri[len(prefix):])
            except OSError as e:
                raise FileNotFoundError(str(e))
            else:
                break
    else:
        if "://" in uri:
            raise FileNotFoundError(f"{uri} not on local filesystem")
        else:
            local_path = uri
    return local_path

def is_user_writeable_uri(uri):
    """Is it OK for the user to use the specified URI to save normal documents,
    i.e. as prompted by a file dialog or similar.

    In general, computed and template filesystems won't be allowed here.
    """
    for prefix, path_finder in filesystems_to_local_file.items():
        if uri.startswith(prefix):
            return False
    return True

def fsopen(uri, mode="r"):
    try:
        local_path = filesystem_path(uri)
    except FileNotFoundError:
        for prefix, opener in computed_filesystems.items():
            if uri.startswith(prefix):
                return opener(uri[len(prefix):], mode)
        else:
            raise FileNotFoundError(f"Unsupported URI scheme for {uri}")
    return open(local_path, mode)


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
    about['app'] = app.app_blank_page.encode('utf-8')

    global image_paths
    path = get_image_path("icons")
    if path not in image_paths:
        image_paths.append(path)


def find_first_in_paths(paths, name):
    log.debug(f"find_first_in_paths: searching subdirs {paths}")
    if name.startswith("/"):
        log.debug(f"find_first_in_paths: found absolute path '{name}', not searching {paths}")
        return name
    checked = []
    for toplevel in paths:
        if toplevel is None:
            continue  # skip user/system path separator
        pathname = os.path.normpath(os.path.join(toplevel, name))
        log.debug(f"find_first_in_paths: checking for {name} in {toplevel}")
        if os.path.exists(pathname):
            log.debug(f"find_first_in_paths: found {name} in {toplevel}")
            return pathname
        checked.append(os.path.abspath(os.path.dirname(pathname)))
    else:
        raise OSError(f"find_first_in_paths: '{name}' not found in {checked}")


def find_latest_in_paths(paths, namespec):
    found = []
    for toplevel in paths:
        if toplevel is None:
            continue  # skip user/system path separator
        pathspec = os.path.normpath(os.path.join(toplevel, namespec))
        files = glob.glob(pathspec)
        if files:
            # for f in files:
            #     print os.path.getctime(f), os.path.getmtime(f), f
            found.extend(files)
    if found:
        newest = max(found, key=os.path.getmtime)
        return newest
    return pathspec


def glob_in_paths(paths):
    for toplevel in paths:
        if toplevel is None:
            continue
        wildcard = os.path.join(toplevel, "*")
        for item in glob.glob(wildcard):
            yield item


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
    main sawx directory (e.g. sawx/icons):
        
    import sawx
    image_path = get_image_path("icons", sawx)
    
    will return the absolute path of "omnivore/icons".
    
    An example using the file keyword: if the current module is in the
    sawx/framework directory, then the call to:
    
    get_image_path("icons", file=__file__)
    
    will contain the absolute path to the sawx/framework/icons directory.
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
