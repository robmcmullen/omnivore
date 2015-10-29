import os
import re
import shlex

from omnimon.utils.runtime import get_all_subclasses
from omnimon.utils.file_guess import FileMetadata

import logging
log = logging.getLogger(__name__)


class UndoStack(list):
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.insert_index = 0
        self.save_point_index = 0
        self.batch = self
    
    def is_dirty(self):
        return self.insert_index != self.save_point_index
    
    def set_save_point(self):
        self.save_point_index = self.insert_index
    
    def perform(self, cmd, editor):
        if cmd is None:
            return UndoInfo()
        undo_info = cmd.perform(editor)
        if undo_info.flags.success:
            self.add_command(cmd)
        cmd.last_flags = undo_info.flags
        return undo_info

    def can_undo(self):
        return self.insert_index > 0
    
    def get_undo_command(self):
        if self.can_undo():
            return self[self.insert_index - 1]
    
    def undo(self, editor):
        cmd = self.get_undo_command()
        if cmd is None:
            return UndoInfo()
        undo_info = cmd.undo(editor)
        if undo_info.flags.success:
            self.insert_index -= 1
        cmd.last_flags = undo_info.flags
        return undo_info
    
    def can_redo(self):
        return self.insert_index < len(self)
    
    def get_redo_command(self):
        if self.can_redo():
            return self[self.insert_index]
    
    def redo(self, editor):
        cmd = self.get_redo_command()
        if cmd is None:
            return UndoInfo()
        undo_info = cmd.perform(editor)
        if undo_info.flags.success:
            self.insert_index += 1
        cmd.last_flags = undo_info.flags
        return undo_info
    
    def start_batch(self):
        if self.batch == self:
            self.batch = Batch()
    
    def end_batch(self):
        self.batch = self

    def add_command(self, command):
        self.batch.insert_at_index(command)
    
    def insert_at_index(self, command):
        last = self.get_undo_command()
        if last is not None and last.coalesce(command):
            return
        if command.is_recordable():
            self[self.insert_index:] = [command]
            self.insert_index += 1

    def pop_command(self):
        last = self.get_undo_command()
        if last is not None:
            self.insert_index -= 1
            self[self.insert_index:self.insert_index + 1] = []
        return last
    
    def history_list(self):
        h = [str(c) for c in self]
        return h
    
    def serialize(self):
        s = Serializer()
        for c in self:
            s.add(c)
        return s
    
    def unserialize_text(self, text, manager):
        offset = manager.get_invariant_offset()
        s = TextDeserializer(text, offset)
        for cmd in s.iter_cmds(manager):
            yield cmd
    
    def find_most_recent(self, cmdcls):
        for cmd in reversed(self):
            if isinstance(cmd, cmdcls):
                return cmd
        return None


class StatusFlags(object):
    def __init__(self, *args):
        # True if command successfully completes, must set to False on failure
        self.success = True
        
        # List of errors encountered
        self.errors = []
        
        # Message displayed to the user
        self.message = None
        
        # set to True if the all views of the data need to be refreshed
        self.refresh_needed = False
        
        for flags in args:
            self.add_flags(flags)
    
    def add_flags(self, flags, cmd=None):
        if flags.message is not None:
            self.messages.append(flags.message)
        if flags.errors:
            if cmd is not None:
                self.errors.append("In %s:" % str(cmd))
            for e in flags.errors:
                self.errors.append("  %s" % e)
            self.errors.append("")
        if flags.refresh_needed:
            self.refresh_needed = True


class UndoInfo(object):
    def __init__(self):
        self.index = -1
        self.data = None
        self.flags = StatusFlags()
    
    def __str__(self):
        return "index=%d, flags=%s" % (self.index, str(dir(self.flags)))


class Command(object):
    short_name = None
    serialize_order = [
        ]
    
    def __init__(self):
        self.undo_info = None
        self.last_flags = None

    def __str__(self):
        return "<unnamed command>"
    
    def get_serialized_name(self):
        if self.short_name is None:
            return self.__class__.__name__
        return self.short_name
    
    def coalesce(self, next_command):
        return False
    
    def is_recordable(self):
        return True
    
    def perform(self, document):
        pass
    
    def undo(self, document):
        pass


class Batch(Command):
    """A batch is immutable once created, so there's no need to allow
    intermediate index points.
    """
    def __str__(self):
        return "<batch>"
    
    def perform(self, document):
        for c in self:
            c.perform(document)
    
    def undo(self, document):
        for c in reversed(self):
            c.undo(document)


def get_known_commands():
    s = get_all_subclasses(Command)
    c = {}
    for cls in s:
        if cls.short_name is not None:
            c[cls.short_name] = cls
    return c


# shlex quote routine modified from python 3 to allow [ and ] unquoted for lists
_find_unsafe = re.compile(r'[^\w@%+=:,./[\]-]').search

def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s
    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"


class UnknownCommandError(RuntimeError):
    pass


class Serializer(object):
    known_commands = None
    
    def __init__(self, magic_id, magic_version):
        self.magic_header = self.get_magic(magic_id, magic_version)
        self.serialized_commands = []
    
    @classmethod
    def get_magic(cls, template, version):
        """Return an identifier string used at the top of a file to indicate
        the version of the serialized file
        """
        return "# %s, v%d" % (identifier, version)
    
    def __str__(self):
        lines = [self.magic_header]
        for cmd in self.serialized_commands:
            lines.append(str(cmd))
        return "\n".join(lines)
    
    def add(self, cmd):
        sc = SerializedCommand(cmd)
        self.serialized_commands.append(sc)
    
    @classmethod
    def get_command(cls, short_name):
        if cls.known_commands is None:
            cls.known_commands = command.get_known_commands()
        try:
            return cls.known_commands[short_name]
        except KeyError:
            return UnknownCommandError(short_name)


class TextDeserializer(object):
    def __init__(self, text, magic_id, magic_version):
        lines = text.splitlines(True)
        self.header = lines.pop(0)
        self.lines = lines
        magic_template = Serializer.get_magic(magic_id, magic_version)
        if not self.header.startswith(magic_template):
            raise RuntimeError("Not a %s command file!" % magic_id)
    
    def iter_cmds(self, manager):
        build_multiline = ""
        for line in self.lines:
            if build_multiline:
                line = build_multiline + line
                build_multiline = ""
            else:
                if not line.strip() or line.startswith("#"):
                    continue
            try:
                text_args = shlex.split(line.strip())
            except ValueError, e:
                build_multiline = line
                continue
            cmd = self.unserialize_line(text_args, manager)
            yield cmd
    
    def unserialize_line(self, text_args, manager):
        short_name = text_args.pop(0)
        log.debug("unserialize: short_name=%s, args=%s" % (short_name, text_args))
        cmd_cls = Serializer.get_command(short_name)
        cmd_args = []
        for name, stype in cmd_cls.serialize_order:
            log.debug("  name=%s, type=%s" % (name, stype))
            converter = SerializedCommand.get_converter(stype)
            arg = converter.instance_from_args(text_args, manager, self)
            log.debug("  converter=%s: %s" % (converter.__class__.__name__, repr(arg)))
            cmd_args.append(arg)
        log.debug("COMMAND: %s(%s)" % (cmd_cls.__name__, ",".join([repr(a) for a in cmd_args])))
        cmd = cmd_cls(*cmd_args)
        return cmd


class ArgumentConverter(object):
    stype = None  # Default converter just uses strings
    
    def get_args(self, instance):
        """Return list of strings that can be used to reconstruct the instance
        """
        return str(instance),
    
    def instance_from_args(self, args, manager, deserializer):
        arg = args.pop(0)
        return arg


class FileMetadataConverter(ArgumentConverter):
    stype = "file_metadata"
    
    def get_args(self, instance):
        # Force forward slashes on windows so to prevent backslash escape chars
        return os.path.normpath(instance.uri).replace('\\', '/'), instance.mime
    
    def instance_from_args(self, args, manager, deserializer):
        uri = args.pop(0)
        mime = args.pop(0)
        return FileMetadata(uri=uri, mime=mime)


class TextConverter(ArgumentConverter):
    stype = "text"
    
    def get_args(self, instance):
        """Return list of strings that can be used to reconstruct the instance
        """
        return instance.encode("utf-8"),
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0)
        return text.decode("utf-8")


class BoolConverter(ArgumentConverter):
    stype = "bool"
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0)
        if text == "None":
            return None
        if text == "True" or text == "1":
            return True
        return False


class IntConverter(ArgumentConverter):
    stype = "int"
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0)
        if text == "None":
            return None
        return int(text)


class FloatConverter(ArgumentConverter):
    stype = "float"
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0)
        if text == "None":
            return None
        return float(text)


class PointConverter(ArgumentConverter):
    stype = "point"
    
    def get_args(self, instance):
        if instance is None:
            return None,
        return instance  # already a tuple
    
    def instance_from_args(self, args, manager, deserializer):
        lon = args.pop(0)
        if lon == "None":
            return None
        lat = args.pop(0)
        return (float(lon), float(lat))


class PointsConverter(ArgumentConverter):
    stype = "points"
    
    def get_args(self, instance):
        text = ",".join(["(%s,%s)" % (str(i[0]), str(i[1])) for i in instance])
        return "[%s]" % text,
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0).lstrip("[").rstrip("]")
        if text:
            text = text.lstrip("(").rstrip(")")
            tuples = text.split("),(")
            points = []
            for t in tuples:
                lon, lat = t.split(",", 1)
                points.append((float(lon), float(lat)))
            return points
        return []


class RectConverter(ArgumentConverter):
    stype = "rect"
    
    def get_args(self, instance):
        (x1, y1), (x2, y2) = instance
        return x1, y1, x2, y2
    
    def instance_from_args(self, args, manager, deserializer):
        x1 = args.pop(0)
        y1 = args.pop(0)
        x2 = args.pop(0)
        y2 = args.pop(0)
        return ((x1, y1), (x2, y2))


class ListIntConverter(ArgumentConverter):
    stype = "list_int"
    
    def get_args(self, instance):
        text = ",".join([str(i) for i in instance])
        return "[%s]" % text,
    
    def instance_from_args(self, args, manager, deserializer):
        text = args.pop(0)
        if text.startswith("["):
            text = text[1:]
        if text.endswith("]"):
            text = text[:-1]
        if text:
            vals = text.split(",")
            return [int(i) for i in vals]
        return []


def get_converters():
    s = get_all_subclasses(ArgumentConverter)
    c = {}
    for cls in s:
        c[cls.stype] = cls()
    c[None] = ArgumentConverter()  # Include default converter
    return c

class SerializedCommand(object):
    converters = get_converters()
    
    def __init__(self, cmd):
        self.cmd_name = cmd.get_serialized_name()
        p = []
        for name, stype in [(n[0], n[1]) for n in cmd.serialize_order]:
            p.append((stype, getattr(cmd, name)))
        self.params = p

    def __str__(self):
        output = []
        for stype, value in self.params:
            try:
                c = self.converters[stype]
                values = c.get_args(value)
            except KeyError:
                values = [value]
            string_values = [quote(str(v)) for v in values]
            output.append(" ".join(string_values))
        
        text = " ".join(output)
        return "%s %s" % (self.cmd_name, text)
    
    @classmethod
    def get_converter(cls, stype):
        try:
            return cls.converters[stype]
        except KeyError:
            return cls.converters[None]
