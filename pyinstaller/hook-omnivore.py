#!/usr/bin/env python
"""
    Added special submodule scanner in for traitsui in the pyinstaller hook
    * with unmodified version, raises RuntimeError when it hits traitsui.qt and fails to import further

"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.hooks import string_types, is_package, get_package_paths, exec_statement

import logging
logger = logging.getLogger(__name__)

DEBUG=False

# Need special version for traitsui because it raises a RuntimeError when
# hitting the traitsui.qt package and doesn't scan any further.
def collect_submodules_traitsui(package, filter=lambda name: True):
    # Accept only strings as packages.
    if not isinstance(package, string_types):
        raise ValueError

    logger.debug('Collecting submodules for %s' % package)
    # Skip a module which is not a package.
    if not is_package(package):
        logger.debug('collect_submodules - Module %s is not a package.' % package)
        return []

    # Determine the filesystem path to the specified package.
    pkg_base, pkg_dir = get_package_paths(package)

    # Walk the package. Since this performs imports, do it in a separate
    # process.
    names = exec_statement("""
        import sys
        import pkgutil

        def ignore_err(name, err):
            # Can't print anything because printing is captured as module names
            # print ("error importing %s: %s" % (name, err))
            pass

        # ``pkgutil.walk_packages`` doesn't walk subpackages of zipped files
        # per https://bugs.python.org/issue14209. This is a workaround.
        def walk_packages(path=None, prefix='', onerror=ignore_err):
            def seen(p, m={{}}):
                if p in m:
                    return True
                m[p] = True

            for importer, name, ispkg in pkgutil.iter_modules(path, prefix):
                if not name.startswith(prefix):   ## Added
                    name = prefix + name          ## Added
                yield importer, name, ispkg

                if ispkg:
                    try:
                        __import__(name)
                    except ImportError as e:
                        if onerror is not None:
                            onerror(name, e)
                    except Exception as e:
                        if onerror is not None:
                            onerror(name, e)
                        else:
                            raise
                    else:
                        path = getattr(sys.modules[name], '__path__', None) or []

                        # don't traverse path items we've seen before
                        path = [p for p in path if not seen(p)]

                        ## Use Py2 code here. It still works in Py3.
                        for item in walk_packages(path, name+'.', onerror):
                            yield item
                        ## This is the original Py3 code.
                        #yield from walk_packages(path, name+'.', onerror)

        for module_loader, name, ispkg in walk_packages([{}], '{}.'):
            print(name)
        """.format(
                  # Use repr to escape Windows backslashes.
                  repr(pkg_dir), package))

    # Include the package itself in the results.
    mods = {package}
    # Filter through the returend submodules.
    for name in names.split():
        if filter(name):
            mods.add(name)

    logger.debug("collect_submodules - Found submodules: %s", mods)
    return list(mods)

def qt_filter(pymod):
    if ".tests" in pymod or ".qt" in pymod or ".null" in pymod:
        logger.debug("qt_filter: skipping %s" % pymod)
        return False
    return True

subpkgs = [
    "traits",
    "pyface",
    "omnivore",
    "omnivore8bit",
    "omnivore",
]

hiddenimports = collect_submodules_traitsui("traitsui", qt_filter)
for s in subpkgs:
    hiddenimports.extend(collect_submodules(s, qt_filter))

if DEBUG or True:
    print("\n".join(sorted(hiddenimports)))

datas = []
skipped = []
for s in subpkgs:
    possible = collect_data_files(s)
    # Filter out stuff.  Handle / and \ for path separators!
    for src, dest in possible:
        if "/qt" not in src and "\\qt" not in src and (".jpg" in src or ".png" in src or ".ico" in src or ".zip" in src):
            datas.append((src, dest))
        elif ("omnivore/omnivore" in src or "omnivore\\omnivore" in src) and ("/help" in src or "/templates" in src or "\\help" in src or "\\templates" in src or ".jpg" in src or ".png" in src or ".ico" in src):
            datas.append((src, dest))
        else:
            skipped.append((src, dest))

if DEBUG:
    print("\n".join(["%s -> %s" % d for d in datas]))
    print("SKIPPED:")
    print("\n".join(["%s -> %s" % d for d in skipped]))
