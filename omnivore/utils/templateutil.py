from atrip.memory_map import MemoryMap
from sawx.persistence import get_template, iter_templates

import logging
log = logging.getLogger(__name__)


machine_labels = {}

def load_memory_map(keyword):
    global machine_labels
    try:
        rwlabels = machine_labels[keyword]
    except KeyError:
        try:
            text = get_template(keyword)
        except OSError as e:
            try:
                text = get_template(keyword + ".labels")
            except OSError as e:
                log.error(f"Couldn't find memory map named '{keyword}'")
                return MemoryMap(keyword)
        rwlabels, rlabels, wlabels = MemoryMap.from_text(keyword, text)
        machine_labels[keyword] = rwlabels  # FIXME: temporary until get sets of memory map labels
    return rwlabels

available_memory_maps = {}

def calc_available_memory_maps():
    global available_memory_maps
    if not available_memory_maps:
        for template in iter_templates("labels"):
            available_memory_maps[template.keyword] = template
    return available_memory_maps
