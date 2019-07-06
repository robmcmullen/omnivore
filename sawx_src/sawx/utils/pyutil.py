import inspect
import pkg_resources

import logging
log = logging.getLogger(__name__)


def iter_sorted_entry_points(entry_point):
    entry_points = []
    for entry_point in pkg_resources.iter_entry_points(entry_point):
        try:
            mod = entry_point.load()
        except Exception as e:
            log.error(f"iter_sorted_entry_points: Failed importing {entry_point.name}: {e}")
            if log.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exc()
        else:
            log.debug(f"iter_sorted_entry_points: Found loader {entry_point.name}, {entry_point.module_name}")
            entry_points.append((entry_point.name, mod))
    mods = [mod for name, mod in sorted(entry_points)]
    log.debug(f"iter_entry_points: sorted modules: {mods}")
    return mods


def get_plugins(entry_point, subclass_of=None):
    """Get modules or classes from an entry point.

    If subclass_of is specified, only classes of that type will be returned.
    Otherwise, the module will be returned.
    """
    possibilities = iter_sorted_entry_points(entry_point)
    if subclass_of is None:
        plugins = possibilities
    else:
        plugins = []
        for mod in possibilities:
            for name, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and subclass_of in obj.__mro__[1:]:
                    # only use actual subclasses, not the subclass_of class
                    log.debug(f"get_plugins:  using plugin class {name}")
                    plugins.append(obj)
    return plugins


def get_all_subclasses_of(parent, subclass_of=None):
    """Get a list of all classes that have a specified class in their ancestry.

    The call to __subclasses__ only finds the direct, child subclasses of an
    object, so to find grandchildren and objects further down the tree, we have
    to go recursively down each subclasses hierarchy to see if the subclasses
    are of the type we want.

    @param parent: class used to find subclasses
    @type parent: class
    @param subclass_of: class used to verify type during recursive calls
    @type subclass_of: class
    @returns: list of classes
    """
    if subclass_of is None:
        subclass_of = parent
    subclasses = {}

    # this call only returns immediate (child) subclasses, not
    # grandchild subclasses where there is an intermediate class
    # between the two.
    classes = parent.__subclasses__()
    for cls in classes:
        # FIXME: this seems to return multiple copies of the same class,
        # but I probably just don't understand enough about how python
        # creates subclasses
        # dprint("%s id=%s" % (cls, id(cls)))
        if issubclass(cls, subclass_of):
            subclasses[cls] = 1
        # for each subclass, recurse through its subclasses to
        # make sure we're not missing any descendants.
        subs = get_all_subclasses_of(cls)
        if len(subs) > 0:
            for cls in subs:
                subclasses[cls] = 1
    return subclasses.keys()
