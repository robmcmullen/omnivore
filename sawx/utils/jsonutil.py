import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy
jsonpickle_numpy.register_handlers()

import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

def collapse_json(text, indent=8, special_keys={}, base_indent=4):
    """Compacts a string of json data by collapsing whitespace after the
    specified indent level with optional keys that can be expanded beyond the
    indent level.
    
    NOTE: will not produce correct results when indent level is not a multiple
    of the json indent level
    """
    initial = " " * indent
    out = []  # final json output
    sublevel = []  # accumulation list for sublevel entries
    pending = None  # holder for consecutive entries at exact indent level
    special = False # are we processing a block that should be expanded
    end_level = 0  # trigger value to determine end of expanded block
    special_lines = []
    special_indent = 0
    remove_next_indent = True  # flag for special case to add indent to line following expanded block
    for line in text.splitlines():
        first_non_blank = len(line) - len(line.lstrip())
        if special:
            special_lines.append(line)
            if first_non_blank == end_level:
                subtext = "\n".join(special_lines)
                log.debug("formatting subblock with %d" % special_indent)
                log.debug(subtext)
                subtext = collapse_json(subtext, special_indent)
                log.debug("formatted subblock:")
                log.debug(subtext)
                log.debug("Resetting to normal.")
                special = False
                out.append(subtext)
                remove_next_indent = False
            continue
        if line.startswith(initial):

            # special expanded keys must be dictionary entries in the json, so
            # they will end with ':'
            keys = line.strip().split(":")
            if not special and len(keys) > 1:
                key = keys[0][1:-1]  # remove quotes
                if key in special_keys:
                    extra_levels = special_keys[key]
                    special_indent = (extra_levels * base_indent) + first_non_blank
                    log.debug("Found %s: %d*%d + %d = %d" % (key, extra_levels, base_indent, indent, special_indent))
                    special = True
                    end_level = first_non_blank
                    special_lines = [line]
                    if sublevel:
                        out.append("".join(sublevel))
                        sublevel = []
                    if pending:
                        out.append(pending)
                        pending = None
                    continue

            # lines following a specially indented block wouldn't ordinarily
            # have an indent, so force it with this flag
            if remove_next_indent:
                item = line.strip()
            else:
                item = line.rstrip()

            if line[indent] == " ":
                # found a line indented further than the indent level, so add
                # it to the sublevel list
                if pending:
                    # the first item in the sublevel will be the pending item
                    # that was the previous line in the json
                    sublevel.append(pending)
                    pending = None
                sublevel.append(item)
                if item.endswith(","):
                    sublevel.append(" ")
            elif sublevel:
                # found a line at the exact indent level *and* we have sublevel
                # items. This means the sublevel items have come to an end
                sublevel.append(item)
                out.append("".join(sublevel))
                sublevel = []
            else:
                # found a line at the exact indent level but no items indented
                # further, so possibly start a new sub-level
                if pending:
                    # if there is already a pending item, it means that
                    # consecutive entries in the json had the exact same
                    # indentation and that last pending item was not the start
                    # of a new sublevel.
                    out.append(pending)
                pending = line.rstrip()
        else:
            if pending:
                # it's possible that an item will be pending but not added to
                # the output yet, so make sure it's not forgotten.
                out.append(pending)
                pending = None
            if sublevel:
                out.append("".join(sublevel))
            out.append(line)
        remove_next_indent = True
    if sublevel:
        out.append("".join(sublevel))
    return "\n".join(out)


def dict_to_list(d):
    """Return a sorted list of lists that represent the dictionary.

    Only strings are allowed as keys in a json dictionary, so this transform
    the dictionary into a list of lists that can be serialized in as small
    amount of text as possible. Tuples would be more efficient in python terms,
    but json can't serialize tuples directly either.
    """
    return sorted([list(i) for i in list(d.items())])

def unserialize(name, text):
    try:
        if hasattr(text, 'decode'):
            text = text.decode('utf-8')
        if text.startswith("#"):
            header, text = text.split("\n", 1)
        unserialized = jsonpickle.loads(text)
    except ValueError as e:
        log.error(f"JSON parsing error for extra metadata: {str(e)}")
        import traceback
        traceback.print_exc()
        unserialized = {}
    except AttributeError as e:
        log.error(f"JSON library error: {str(e)}")
        import traceback
        traceback.print_exc()
        unserialized = {}
    return unserialized

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.WARNING)


    s = {"zero": ["first", {"second": 2, "third": 3, "fourth": 4, "items": [[1,2,3,4], [5,6,7,8], 9, 10, [11, [12, [13, [14, 15]]]]], "items2": [[1,2,3,4], [5,6,7,8], 9, 10, [11, [12, [13, [14, 15]]]]]}],"zeroprime": [10,[12,[14, 16]]]}

    text = json.dumps(s, indent=4)
    print("original")
    print(text)

    def process(level):
        processed = collapse_json(text, indent=level, special_keys = {"viewers": 1, "linked bases": 1, "items2": 1})
        print(level)
        print(processed)
        rebuilt = json.loads(processed)
        assert rebuilt == s

    for level in range(0, 21, 4):
        process(level)
