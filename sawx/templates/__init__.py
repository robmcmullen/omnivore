import os
import json

from .. import filesystem

import logging
log = logging.getLogger(__name__)


def get_template_fh(name):
    # resource path will point to the omnivore/templates directory
    pathname = filesystem.find_template_path(name)
    log.debug("Loading template for %s: %s" % (name, pathname))
    fh = open(pathname, "rb")
    return fh


def get_template(name):
    # resource path will point to the omnivore/templates directory
    fh = get_template_fh(name)
    source = fh.read()
    return source


class TemplateItem(dict):
    def __init__(self, data_file_path, keyword, inf_type, json_dict):
        dict.__init__(self)
        self.data_file_path = data_file_path
        self.keyword = keyword
        self.inf_type = inf_type
        self._data_bytes = None
        for k, v in json_dict.items():
            self[k] = v
            setattr(self, k, v)

    def __str__(self):
        return self.get("label", "") or self.get("description", "") or self.get("name", "") or self.keyword

    def __lt__(self, other):
        return str(self) < str(other)

    @property
    def data_bytes(self):
        if not self._data_bytes:
            with open(self.data_file_path, 'rb') as fh:
                self._data_bytes = fh.read()
        return self._data_bytes


def iter_templates(inf_type=None):
    """Returns dictionary containing info about specific template types

    Dict contains keys:

    * pathname  - the full pathname to the template to differentiate default
      and user templates with the same name
    * uri
    * task  - editor name
    """
    templates = {}
    for template_path in filesystem.glob_in_paths(filesystem.template_paths):
        if template_path.endswith(".inf"):
            # skip loading inf files
            continue
        inf_path = template_path + ".inf"
        j = None
        if os.path.exists(template_path) and os.path.isfile(template_path):
            log.debug(f"checking template {template_path} for {inf_type}")
            keyword = os.path.basename(template_path)
            keyword2, ext = os.path.splitext(keyword)
            if ext and ext[1:] == inf_type:
                keyword = keyword2
                ext = inf_type
            if os.path.exists(inf_path):
                try:
                    log.debug("Loading json file %s" % inf_path)
                    with open(inf_path, "r") as fh:
                        j = json.loads(fh.read())
                except ValueError as e:
                    log.error(f"Template properties error in {inf_path}: {e}")
                    continue
                if inf_type:
                    if "type" not in j and ext and ext != inf_type:
                        continue
                    elif "type" in j and j["type"] != inf_type:
                        continue
                j["pathname"] = template_path
                j["uri"] = "template://" + template_path
                if "task" in j and j["task"] == "hex_edit":
                    j["task"] = "byte_edit"
            elif ext == inf_type:
                j = {}
                j["type"] = inf_type
                j["pathname"] = template_path
                j["uri"] = "template://" + template_path
            if j is not None:
                item = TemplateItem(template_path, keyword, inf_type, j)
                log.debug(f"template: {item}")
                yield item
