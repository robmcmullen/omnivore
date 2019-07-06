import os
import re
import shlex

from .runtime import get_all_subclasses
# from .file_guess import FileMetadata

import logging
log = logging.getLogger(__name__)


class HistoryList(list):
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.insert_index = 0
        self.save_point_index = 0

    def __str__(self):
        text = ""
        for i, s in enumerate(self.history_list()):
            if i == self.insert_index:
                text += "  ---> insert index\n"
            text += s + "\n"
        if self.insert_index == len(self):
            text += "  ---> insert index\n"
        return text

    def is_dirty(self):
        return self.insert_index != self.save_point_index

    def set_save_point(self):
        self.save_point_index = self.insert_index

    @property
    def can_undo(self):
        return self.insert_index > 0

    @property
    def can_redo(self):
        return self.insert_index < len(self)

    def history_list(self):
        h = [str(c) for c in self]
        return h

    def get_undo_command(self):
        if self.can_undo:
            return self[self.insert_index - 1]

    def get_redo_command(self):
        if self.can_redo:
            return self[self.insert_index]

    def add_command(self, command):
        self[self.insert_index:] = [command]
        self.insert_index += 1

    def prev_command(self):
        cmd = self.get_undo_command()
        if cmd is not None:
            self.insert_index -= 1
        return cmd

    def next_command(self):
        cmd = self.get_redo_command()
        if cmd is not None:
            self.insert_index += 1
        return cmd


class UndoStack(HistoryList):
    def __init__(self, *args, **kwargs):
        HistoryList.__init__(self, *args, **kwargs)
        self.batch = self

    def perform_setup(self, editor):
        pass

    def perform(self, cmd, editor, batch=None):
        if cmd is None:
            return UndoInfo(editor)
        if batch != self.batch:
            if batch is None:
                self.end_batch()
            else:
                if self.batch is not None:
                    self.end_batch()
                self.start_batch(batch)
        self.batch.perform_setup(editor)
        undo_info = UndoInfo(editor)
        cmd.perform(editor, undo_info)
        if undo_info.flags.changed_document:
            if undo_info.flags.success:
                self.add_command(cmd)
            cmd.last_flags = undo_info.flags
        return undo_info

    def undo(self, editor):
        cmd = self.get_undo_command()
        if cmd is None:
            return UndoInfo(editor)
        undo_info = cmd.undo(editor)
        if undo_info.flags.success:
            self.insert_index -= 1
        cmd.last_flags = undo_info.flags
        return undo_info

    def redo(self, editor):
        cmd = self.get_redo_command()
        if cmd is None:
            return UndoInfo(editor)
        undo_info = UndoInfo(editor)
        cmd.perform(editor, undo_info)
        if undo_info.flags.success:
            self.insert_index += 1
        cmd.last_flags = undo_info.flags
        return undo_info

    def start_batch(self, batch):
        self.batch = batch
        log.debug("Starting batch %s" % self.batch)

    def end_batch(self):
        log.debug("Ending batch %s" % self.batch)
        if self.batch != self:
            batch_command = self.batch.get_recordable_command()
            if batch_command is not None:
                self.batch = self
                self.add_command(batch_command)

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

        # True if command made a change to the document and therefore should be recorded
        self.changed_document = True

        # List of errors encountered
        self.errors = []

        # Message displayed to the user
        self.message = ""

        # has any data values changed, forcing all views to be refreshed?
        self.byte_values_changed = False

        # has any data style changed, forcing all views to be refreshed?
        self.byte_style_changed = False

        # has anything in the data or metadata changed to require a rebuild
        # of the data model?
        self.data_model_changed = False

        # set to True if the all views of the data need to be refreshed
        self.refresh_needed = False

        # ensure the specified index is visible
        self.index_visible = None

        # ensure the specified index range is visible
        self.index_range = None

        # set to True if the index_range should be selected
        self.select_range = False

        # set caret index to position
        self.caret_index = None

        # keep any selection instead of erasing during a caret move
        self.keep_selection = None

        # set caret column to position, if supported
        self.caret_column = None

        # set if document properties have changed, but not the actual data
        self.metadata_dirty = None

        # set if user interface needs to be updated (very heavyweight call!)
        self.rebuild_ui = None

        # the source control on which the event happened, if this is the
        # result of a user interface change
        self.source_control = None

        # if the source control is refreshed as a side-effect of some action,
        # set this flag so that the event manager can skip that control when
        # it refreshes the others
        self.skip_source_control_refresh = False

        # if the portion of the window looking at the data needs to be changed,
        # these will be the new upper left coordinates
        self.viewport_origin = None

        # list of viewers that have been refreshed during the caret_flags
        # processing so it won't be updated again
        self.refreshed_as_side_effect = set()

        # set if the user is selecting by entire rows
        self.selecting_rows = False

        # if not None, will contain the set carets to determine if any have
        # moved and need to be updated.
        self.old_carets = None

        # if True will add the old carets to the current caret to increase the
        # number of carets by one
        self.add_caret = False

        # if True will remove all carets except the current caret
        self.force_single_caret = False

        # move the caret(s) to the next edit position (usually column) using
        # the control as the basis for how much the index needs to be adjusted
        # to get to the next column.
        self.advance_caret_position_in_control = None

        for flags in args:
            self.add_flags(flags)

    def __str__(self):
        flags = []
        for name in dir(self):
            if name.startswith("_"):
                continue
            val = getattr(self, name)
            if val is None or not val or hasattr(val, "__call__"):
                continue
            flags.append("%s=%s" % (name, val))
        return ", ".join(flags)

    def add_flags(self, flags, cmd=None):
        if flags.message is not None:
            self.message += flags.message
        if flags.errors:
            if cmd is not None:
                self.errors.append("In %s:" % str(cmd))
            for e in flags.errors:
                self.errors.append("  %s" % e)
            self.errors.append("")
        if flags.byte_values_changed:
            self.byte_values_changed = True
        if flags.byte_style_changed:
            self.byte_style_changed = True
        if flags.refresh_needed:
            self.refresh_needed = True
        if flags.select_range:
            self.select_range = True
        if flags.metadata_dirty:
            self.metadata_dirty = True
        if flags.rebuild_ui:
            self.rebuild_ui = True

        # Expand the index range to include the new range specified in flags
        if flags.index_range is not None:
            if self.index_range is None:
                self.index_range = flags.index_range
            else:
                s1, s2 = self.index_range
                f1, f2 = flags.index_range
                if f1 < s1:
                    s1 = f1
                if f2 > s2:
                    s2 = f1
                self.index_range = (s1, s2)

        if flags.caret_index is not None:
            self.caret_index = flags.caret_index
        if flags.caret_column is not None:
            self.caret_column = flags.caret_column
        if flags.force_single_caret:
            self.force_single_caret = flags.force_single_caret
        if flags.keep_selection:
            self.keep_selection = flags.keep_selection
        if flags.source_control:
            self.source_control = flags.source_control
        if flags.advance_caret_position_in_control:
            self.advance_caret_position_in_control = flags.advance_caret_position_in_control


class DisplayFlags(StatusFlags):
    def __init__(self, source_control=None):
        StatusFlags.__init__(self)
        self.source_control = source_control


class UndoInfo(object):
    def __init__(self, editor):
        self.index = -1
        self.data = None
        self.flags = editor.calc_status_flags()

    def __str__(self):
        return "index=%d, flags=%s" % (self.index, str(dir(self.flags)))


class Command(object):
    short_name = None
    ui_name = "<unnamed command>"
    serialize_order = [
        ]

    def __init__(self):
        self.undo_info = None
        self.last_flags = None

    def __str__(self):
        return self.ui_name

    def get_serialized_name(self):
        if self.short_name is None:
            return self.__class__.__name__
        return self.short_name

    def can_coalesce(self, next_command):
        """Evaluate whether or not the next command can be merged into this
        command.

        The difference between this and coalesce below is coalesce will take
        care of the very basics of comparisons and only send on commands that
        are of the same class.
        """
        return False

    def coalesce_merge(self, next_command):
        """Merge the next command into self

        Takes the details of next_command and combines them into the current
        instance. This is very implementation dependent, but the key is that
        the merged command must be undoable to the state before the current
        command.
        """
        raise NotImplementedError

    def coalesce(self, next_command):
        """If the next command can be merged with this one, merge them.

        Checks if the next command can be merged, and if so will merge the
        details of the next command into self. The default implementation calls
        can_coalesce to check if it can be merged, and if so calls
        coalesce_merge to actually merge the commands.
        """
        if next_command.__class__ == self.__class__:
            if self.can_coalesce(next_command):
                self.coalesce_merge(next_command)

    def is_recordable(self):
        return True

    def perform_setup(self, document):
        pass

    def do_change(self, editor, undo_info):
        raise NotImplementedError

    def set_undo_flags(self, flags):
        pass

    def perform(self, editor, undo_info):
        old_data = self.do_change(editor, undo_info)
        undo_info.data = (old_data, )
        self.set_undo_flags(undo_info.flags)
        self.undo_info = undo_info

    def undo_change(self, editor, old_data):
        raise NotImplementedError

    def undo(self, editor):
        old_data, = self.undo_info.data
        self.undo_change(editor, old_data)
        return self.undo_info


class Batch(Command):
    """A batch is immutable once created, so there's no need to allow
    intermediate index points.
    """
    ui_name = "<batch>"

    def __init__(self):
        Command.__init__(self)
        self.commands = []

    def get_recordable_command(self):
        return self

    def perform(self, document, undo_info):
        flags = StatusFlags()
        for c in self.commands:
            undo = c.perform(document)
            flags.add_flags(undo.flags)
        undo_info.flags = flags

    def undo(self, document):
        flags = StatusFlags()
        for c in reversed(self.commands):
            undo = c.undo(document)
            flags.add_flags(undo.flags)
        undo = UndoInfo()
        undo.flags = flags
        return undo

    def insert_at_index(self, command):
        if command.is_recordable():
            self.commands.append(command)


class Overlay(Command):
    ui_name = "<overlay>"

    def __init__(self):
        Command.__init__(self)
        self.last_command = None

    def get_recordable_command(self):
        return self.last_command

    def perform_setup(self, document):
        flags = StatusFlags()
        last = self.last_command
        if last is not None:
            undo = last.undo(document)
            flags.add_flags(undo.flags)
        undo = UndoInfo(editor)
        undo.flags = flags
        return undo

    def undo(self, document):
        # Not used because the overlay is replaced by the last command.  See
        # get_recordable_command above
        pass

    def insert_at_index(self, command):
        self.last_command = command


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
            except ValueError as e:
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
