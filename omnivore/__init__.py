# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__author__ = "Rob McMullen"
__author_email__ = "feedback@playermissile.com"
__url__ = "http://playermissile.com/omnivore"
__download_url__ = "https://github.com/robmcmullen/omnivore/archive"
__bug_report_url__ = "https://github.com/robmcmullen/omnivore/issues"

# The real version number is maintained in a file that's under version control
# so I don't have to keep updating and checking in the file
try:
    import _omnivore_version
    __version__ = _omnivore_version.version
except ImportError:
    __version__ = "dev"

import logging
log = logging.getLogger(__name__)


# py2exe utilities
def get_py2exe_toolkit_includes(module=None, toolkit="wx"):
    """Get a list of modules that should be included in a py2exe/py2app
    distribution but because they are imported dynamically must be explicitly
    included.
    
    This list of files should be added to options keyword parameter of the
    setup call; e.g:
    
    setup(options={"py2exe": {"includes": omnivore.get_py2exe_toolkit_includes()}})
    """
    if module is None:
        path = __file__
    else:
        path = module.__file__
    import os
    basedir, module = os.path.split(os.path.dirname(path))
    #print basedir, module
    suffix = "_%s.py" % toolkit
    includes = []
    for root, dirs, files in os.walk(os.path.join(basedir, module)):
        #print root, files
        mod_root = root[len(basedir) + 1:]
        needed = [f for f in files if f.endswith(suffix)]
        for f in needed:
            mod_name = ("%s.%s" % (mod_root, f[:-3])).replace("/", ".").replace("\\", ".")
            includes.append(mod_name)
    return includes


def get_py2exe_data_files(module=None, excludes=[]):
    """Get a list of data files that should be included in a py2exe/py2app
    distribution's data files parameter.
    
    The returned list should be added to the data_files keyword parameter of the
    setup call; e.g:
    
    data_files = []
    import omnivore
    data_files.extend(omnivore.get_py2exe_data_files())
    setup(..., data_files=data_files, ...)
    """
    # added .zip files for pyface image libraries
    extensions = [".png", ".jpg", ".ico", ".zip"]

    if module is None:
        path = __file__
    else:
        path = module.__file__
    import os
    import fnmatch
    basedir, module = os.path.split(os.path.dirname(path))
    #print basedir, module
    data_files = []
    for root, dirs, files in os.walk(os.path.join(basedir, module)):
        #print root, files
        mod_root = root[len(basedir) + 1:]
        needed = []
        for f in files:
            for suffix in extensions:
                if f.endswith(suffix):
                    path = os.path.join(root, f)
                    for pattern in excludes:
                        if fnmatch.fnmatch(path, pattern):
                            path = None
                            break
                    if path:
                        needed.append(path)
                        break
        if needed:
            data_files.append((mod_root, needed))
    return data_files


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
    main omnivore directory (e.g. omnivore/icons):
        
    import omnivore
    image_path = get_image_path("icons", omnivore)
    
    will return the absolute path of "omnivore/icons".
    
    An example using the file keyword: if the current module is in the
    omnivore/framework directory, then the call to:
    
    get_image_path("icons", file=__file__)
    
    will contain the absolute path to the omnivore/framework/icons directory.
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
