# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "https://github.com/robmcmullen/peppy2"
__download_url__ = "https://github.com/robmcmullen/peppy2/releases"
__bug_report_url__ = "https://github.com/robmcmullen/peppy2/issues"
__keywords__ = "text editor, python, plugins"
__license__ = "GPL"
__requires__ = [
    'traits',
    'pyface',
    'traitsui',
    'apptools',
    'envisage',
]

# The real version number is maintained in a file that's under version control
# so I don't have to keep updating and checking in the file
try:
    import _peppy_version
    __version__ = _peppy_version.version
    __codename__ = _peppy_version.codename
    __revision__ = _peppy_version.revision
except ImportError:
    __version__ = "0.1.dev"
    __codename__ = "git-codename"
    __revision__ = "HEAD"


# py2exe utilities
def get_py2exe_toolkit_includes(module=None, toolkit="wx"):
    """Get a list of modules that should be included in a py2exe/py2app
    distribution but because they are imported dynamically must be explicitly
    included.
    
    This list of files should be added to options keyword parameter of the
    setup call; e.g:
    
    setup(options={"py2exe": {"includes": peppy2.get_py2exe_toolkit_includes()}})
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
    import peppy2
    data_files.extend(peppy2.get_py2exe_data_files())
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

def get_image_path(rel_path, module=None, excludes=[]):
    """Get the image path for static images relative to the specified module
    
    The image path will be modified to find images in py2exe/py2app
    locations assuming that the data files have been added using the above
    get_py2exe_data_files function.
    
    For example, in peppy2, the images are located in a directory "icons" in
    main peppy2 directory (e.g. peppy2/icons):
        
    import peppy2
    image_path = get_image_path("icons", peppy2)
    
    will return the absolute path of "peppy2/icons".
    """
    if module is None:
        path = __file__
    else:
        path = module.__file__
    import os
    import sys
    frozen = getattr(sys, 'frozen', False)
    image_path = os.path.join(os.path.dirname(path), rel_path)
    if frozen:
        if frozen in ('macosx_app'):
            #print "FROZEN!!! %s" % frozen
            root = os.environ['RESOURCEPATH']
            zippath, image_path = image_path.split(".zip/")
            image_path = os.path.join(root, image_path)
        else:
            print "App packager %s not yet supported for image paths!!!"
    return image_path
