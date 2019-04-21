import os
import sys
import glob
import json
import pkg_resources

import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy
jsonpickle_numpy.register_handlers()
from .ui import fonts  # register wxFont jsonpickle handler

from datetime import datetime

import appdirs
from . import filesystem

import logging
log = logging.getLogger(__name__)


# Custom jsonpickle handlers

import wx

class wxColorHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        data["rgba"] = [obj.Red(), obj.Green(), obj.Blue(), obj.Alpha()]
        return data

    def restore(self, obj):
        r, g, b, a = obj["rgba"]
        return wx.Colour(r, g, b, a)

jsonpickle.handlers.registry.register(wx.Colour, wxColorHandler)




config_base_dir = None
log_dir = None
log_file_ext = None
cache_dir = None
user_data_dir = None
template_dir = None

def setup_file_persistence(app_name):
    global config_base_dir, log_dir, log_file_ext, cache_dir, user_data_dir, template_dir

    dirname = appdirs.user_config_dir(app_name)
    config_base_dir = dirname
    template_dir = get_config_subdir("templates")
    filesystem.template_paths[0:0] = [template_dir]

    # Make sure it exists!
    if not os.path.exists(config_base_dir):
        os.makedirs(config_base_dir)

    dirname = appdirs.user_log_dir(app_name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    log_dir = dirname

    log_file_ext = "-%s" % datetime.now().strftime("%Y%m%d-%H%M%S")

    dirname = appdirs.user_cache_dir(app_name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    cache_dir = dirname

    dirname = appdirs.user_data_dir(app_name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    user_data_dir = dirname

    # Prevent py2exe from creating a dialog box on exit saying that there
    # are error messages.  It thinks that anything written to stderr is an
    # error, and the python logging module redirects everything to stderr.
    # Instead, redirect stderr to a log file in the user log directory
    frozen = getattr(sys, 'frozen', False)
    if frozen in ('dll', 'windows_exe', 'console_exe'):
        # redirect py2exe stderr/stdout to log file
        log = get_log_file_name("py2exe")
        oldlog = sys.stdout
        sys.stdout = open(log, 'w')
        if hasattr(oldlog, "saved_text"):
            sys.stdout.write("".join(oldlog.saved_text))
        sys.stderr = sys.stdout

        # The logging module won't redirect to the new stderr without help
        handler = logging.StreamHandler(sys.stderr)
        logger = logging.getLogger('')
        logger.addHandler(handler)
    else:
        log = get_log_file_name("log")
        handler = logging.FileHandler(log)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(msg)s")
        handler.setFormatter(formatter)
        logger = logging.getLogger('')
        logger.addHandler(handler)

def get_log_file_name(log_file_name_base, ext=""):
    filename = log_file_name_base + log_file_ext
    if ext:
        if not ext.startswith("."):
            filename += "."
        filename += ext
    else:
        filename += ".log"
    filename = os.path.join(log_dir, filename)
    return filename

def save_log(text, log_file_name_base, ext=""):
    filename = get_log_file_name(log_file_name_base, ext)

    try:
        with open(filename, "w") as fh:
            fh.write(text)
    except IOError:
        log.error("Failed writing %s to %s" % (log_file_name_base, filename))

def get_config_subdir(subdir):
    dirname = os.path.join(config_base_dir, subdir)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname

def get_config_dir_filename(storage_type, json_name):
    return os.path.join(config_base_dir, json_name + "." + storage_type)

def get_file_config_data(subdir, filename, default_on_error=None, mode='r'):
    try:
        file_path = get_config_dir_filename(subdir, filename)
        with open(file_path, mode) as fh:
            data = fh.read()
        return data
    except IOError:
        # file not found
        return default_on_error

def save_file_config_data(subdir, filename, data, mode='w'):
    file_path = get_config_dir_filename(subdir, filename)
    with open(file_path, mode) as fh:
        fh.write(data)
    return file_path

def get_json_data(json_name, default_on_error=None):
    raw = get_file_config_data("json", json_name)
    if raw is None:
        return default_on_error
    try:
        decoded = jsonpickle.decode(raw)
        try:
            # legacy format is a list with a format identifier as the first
            # entry
            if decoded[0] == "format=v2":
                decoded = decoded[1]
        except KeyError:
            pass
        return decoded
    except ValueError:
        # bad JSON format
        log.error("Bad JSON format in preferences file: %s" % json_name)
        return default_on_error

def save_json_data(json_name, data):
    encoded = jsonpickle.encode(data)
    return save_file_config_data("json", json_name, encoded)

def get_bson_data(bson_name):
    import bson

    raw = get_file_config_data("bson", bson_name, mode='rb')
    if raw is not None and len(raw) > 0:
        bson_data = bson.loads(raw)
        data = bson_data[bson_name]
    else:
        raise IOError("Blank BSON data")
    return data

def save_bson_data(bson_name, data):
    import bson

    bson_data = {bson_name: data}
    raw = bson.dumps(bson_data)
    save_file_config_data("bson", bson_name, raw, mode='wb')

def get_user_dir(subdir):
    dirname = os.path.join(user_data_dir, subdir)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname

def get_user_dir_filename(subdir, json_name):
    return os.path.join(get_user_dir(subdir), json_name)

def get_user_data(subdir, filename, default_on_error=None, mode='r'):
    try:
        file_path = get_user_dir_filename(subdir, filename)
        with open(file_path, mode) as fh:
            data = fh.read()
        return data
    except IOError:
        # file not found
        return default_on_error

def save_user_data(subdir, filename, data, mode='w'):
    file_path = get_user_dir_filename(subdir, filename)
    with open(file_path, mode) as fh:
        fh.write(data)

def get_available_user_data(subdir):
    config_dir = get_user_dir(subdir)
    globname = os.path.join(config_dir, "*")
    available = [os.path.basename(a) for a in glob.glob(globname)]
    return available

def get_text_user_data(subdir, filename, default_on_error=None):
    return get_user_data(subdir, filename, default_on_error, 'r')

def save_text_user_data(subdir, filename, data):
    return save_user_data(subdir, filename, data)

def get_binary_user_data(subdir, filename, default_on_error=None):
    return get_user_data(subdir, filename, default_on_error, 'rb')

def save_binary_user_data(subdir, filename, data):
    return save_user_data(subdir, filename, data, 'wb')

def get_cache_dir(subdir):
    dirname = os.path.join(cache_dir, subdir)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname


# Templates

def get_template_fh(name, include_user_defined=True):
    # resource path will point to the omnivore/templates directory
    pathname = filesystem.find_template_path(name, include_user_defined)
    log.debug("Loading template for %s: %s" % (name, pathname))
    fh = filesystem.fsopen(pathname, "rb")
    return fh

def get_template(name, include_user_defined=True):
    # resource path will point to the omnivore/templates directory
    fh = get_template_fh(name, include_user_defined)
    source = fh.read()
    return source

def save_template(name, contents, binary=True):
    pathname = os.path.normpath(os.path.join(template_dir, name))
    if binary:
        mode = "wb"
    else:
        mode = "w"
    fh = filesystem.fsopen(pathname, mode)
    fh.write(contents)

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


# Remember hooks

def restore_from_last_time():
    modules = []
    for entry_point in pkg_resources.iter_entry_points('sawx.remember'):
        try:
            mod = entry_point.load()
        except Exception as e:
            log.error(f"Failed importing remember entry point {entry_point.name}: {e}")
            import traceback
            traceback.print_exc()
        else:
            log.debug(f"restore_from_last_time: Found module {entry_point.name}")
            try:
                restore = getattr(mod, 'restore_from_last_time')
            except AttributeError:
                log.warning(f"restore_from_last_time: no restore function in module {entry_point.name}")
            else:
                restore()
                modules.append(mod)
    return modules


def remember_for_next_time(modules):
    for mod in modules:
        log.debug(f"remember_for_next_time: {mod}")
        try:
            remember = getattr(mod, 'remember_for_next_time')
        except AttributeError:
            log.warning(f"remember_for_next_time: no remember function in module {mod}")
        else:
            remember()
