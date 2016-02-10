from pyface.tasks.topological_sort import topological_sort

def find_wildcard_matches(item_map, pattern):
    if pattern.endswith("*"):
        pattern = pattern[:-1]
    if pattern:
        for id, item in item_map.iteritems():
            if id.startswith(pattern):
                yield item

def before_after_wildcard_sort(items):
    """ Sort a sequence of items with 'before', 'after', and 'id' attributes.
        
    The sort is topological. If an item does not specify a 'before' or 'after',
    it is placed after the preceding item.
    
    Simple wildcards are allowed in the 'before' or 'after' attributes.  The
    asterisk must be the last character in the string, so the form "text*"
    will match any id that starts with "text".

    If a cycle is found in the dependencies, a warning is logged and the order
    of the items is undefined.
    """
    # Handle a degenerate case for which the logic below will fail (because
    # prev_item will not be set).
    if len(items) < 2:
        return items

    # Build a set of pairs representing the graph.
    item_map = dict((item.id, item) for item in items if item.id)
    pairs = []
    prev_item = None
    for item in items:
        # Attempt to use 'before' and 'after' to make pairs.
        new_pairs = []
        if hasattr(item, 'before') and item.before:
            if item.before.endswith("*"):
                for child in find_wildcard_matches(item_map, item.before):
#                    print "%s should be before %s" % (item.id, child.id)
                    new_pairs.append((item, child))
            else:
                child = item_map.get(item.before)
                if child:
                    new_pairs.append((item, child))
        if hasattr(item, 'after') and item.after:
            if item.after.endswith("*"):
                for parent in find_wildcard_matches(item_map, item.after):
#                    print "%s should be after %s" % (item.id, parent.id)
                    new_pairs.append((parent, item))
            else:
                parent = item_map.get(item.after)
                if parent:
                    new_pairs.append((parent, item))

        # If we have any pairs, use them. Otherwise, use the previous unmatched
        # item as a parent, if possible.
        if new_pairs:
            pairs.extend(new_pairs)
        else:
            if prev_item:
                pairs.append((prev_item, item))
            prev_item = item

    # Now perform the actual sort.
    result, has_cycle = topological_sort(pairs)
    if has_cycle:
        logger.warning('Cycle in before/after sort for items %r', items)
    return result
    
def collapse_overlapping_ranges(ranges):
    """ Collapse the list of (possibly overlapping) selected ranges into
    a monotonically increasing set of non-overlapping ranges
    """
    opt = []
    start, end = None, None
    for next_start, next_end in sorted(ranges):
        if next_start > next_end:
            next_start, next_end = next_end, next_start
        if start is None:
            start, end = next_start, next_end
        else:
            if next_start > end:
                opt.append((start, end))
                start, end = next_start, next_end
            elif next_end > end:
                end = next_end
    if start is not None:
        opt.append((start, end))
    return opt
    
def invert_ranges(ranges, last):
    """ Invert the list of (possibly overlapping) selected ranges into a
    monotonically increasing set of non-overlapping ranges that represents the
    opposite of the listed ranges
    """
    # get a monotonically increasing list
    ranges = collapse_overlapping_ranges(ranges)
    inverted = []
    
    first = 0
    for start, end in ranges:
        if start > first:
            inverted.append((first, start))
            first = end
        else:
            first = end
    if first < last:
        inverted.append((first, last))
    return inverted
