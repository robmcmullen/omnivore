import logging
log = logging.getLogger(__name__)


def split_path(path):
    parts = path.split(" -> ")[0:-1]  # skip the last one, it's blank
    print parts
    return parts[-1], len(parts)

def parse_hierarchy(hierarchy):
    menus = []
    current_path = ""
    current_menu = []
    title = ""
    level = 0
    for path, action in hierarchy:
        if action is None:  # found a submenu
            print "MENU", path
            current_path = path
            title, level = split_path(path)
        else:
            print "ACTION", level, title, action.name, action.tooltip

