import numpy as np

from pyface.tasks.topological_sort import topological_sort

import logging
log = logging.getLogger(__name__)


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
    unconstrained_pairs = []
    skip_before = set()
    skip_after = set()
    reverse_check = set()
    prev_item = None

    # Move all doubly-constrained items to the end
    items_front = []
    items_back = []
    for item in items:
        wildcard_before = False
        wildcard_after = False
        if hasattr(item, 'before') and item.before and item.before.endswith("*"):
            wildcard_before = True
        if hasattr(item, 'after') and item.after and item.after.endswith("*"):
            wildcard_after = True
        if wildcard_before or wildcard_after:
            items_back.append(item)
        else:
            items_front.append(item)
    items = items_front
    items.extend(items_back)
    log.debug("item parse order: %s" % ", ".join([a.id for a in items]))

    for item in items:
        # Attempt to use 'before' and 'after' to make pairs.
        before_pairs = []
        after_pairs = []
        wildcard_before = False
        wildcard_after = False
        if hasattr(item, 'before') and item.before:
            if item.before.endswith("*"):
                wildcard_before = True
                for child in find_wildcard_matches(item_map, item.before):
#                    print "%s should be before %s" % (item.id, child.id)
                    before_pairs.append((item, child))
            else:
                child = item_map.get(item.before)
                if child:
                    before_pairs.append((item, child))
        if hasattr(item, 'after') and item.after:
            if item.after.endswith("*"):
                wildcard_after = True
                for parent in find_wildcard_matches(item_map, item.after):
#                    print "%s should be after %s" % (item.id, parent.id)
                    if item.id in skip_after:
                        log.debug("Not including %s > %s because of earlier constraint" % (parent.id, item.id))
                    elif parent.id != item.id:
                        after_pairs.append((parent, item))
                    else:
                        log.debug("Can't be after itself! %s" % item.id)
                skip_after.add(item.id)
            else:
                parent = item_map.get(item.after)
                if parent:
                    after_pairs.append((parent, item))

        # simple cycle check: remove any single item named in the before/after
        # list from the wildcard in the after/before
        if wildcard_before and not wildcard_after and after_pairs:
            # check for single 'after' item in the list of items in 'before'
            dup_item = after_pairs[0][0]
            for i, (list_item, child) in enumerate(before_pairs):
                if dup_item.id == child.id and list_item.id == item.id:
                    log.debug("%s > %s required; %s > %s generates %s > %s which must be removed from after" % (item.after, item.id, item.id, item.before, dup_item.id, list_item.id))
                    log.debug("Removed %s from before list: (%s, %s)" % (dup_item.id, list_item.id, child.id))
                    before_pairs[i:i+1] = []
                    break
        elif wildcard_after and not wildcard_before and before_pairs:
            # check for 'before' item in the list of items in 'after'
            dup_item = before_pairs[0][1]
            for i, (parent, list_item) in enumerate(after_pairs):
                if dup_item.id == parent.id and list_item.id == item.id:
                    log.debug("%s > %s required; %s > %s generates %s > %s which must be removed from after" % (item.id, item.before, item.after, item.id, dup_item.id, list_item.id))
                    after_pairs[i:i+1] = []
                    break

        # If we have any pairs, use them. Otherwise, use the previous unmatched
        # item as a parent, if possible.
        if before_pairs or after_pairs:
            if before_pairs:
                pairs.extend(before_pairs)
            if after_pairs:
                pairs.extend(after_pairs)
        else:
            if prev_item:
                log.debug("Using prev_item: %s > %s" % (prev_item.id, item.id))
                unconstrained_pairs.append((prev_item, item))
            prev_item = item

    # check conditional pairs for those items without constraints. Remove any
    # conditional constraint if there is already some constraint for one of the
    # items referenced
    referenced = set()
    for item1, item2 in pairs:
        referenced.add(item1.id)
        referenced.add(item2.id)
    log.debug("ids with constraints: %s" % sorted(referenced))
    addl_pairs = []
    for item1, item2 in unconstrained_pairs:
        need_pair = False
        if item1.id in referenced and item2.id in referenced:
            for p1, p2 in pairs:
                if (item1.id == p1.id or item1.id == p2.id or item2.id == p1.id or item2.id == p2.id) and (p1.id in referenced and p2.id in referenced):
                        log.debug("skipping unconstrained (%s > %s) because a constraint already exists: (%s > %s)" % (item1.id, item2.id, p1.id, p2.id))
                        break
            else:
                need_pair = True
        else:
            need_pair = True

        if need_pair:
            addl_pairs.append((item1, item2))
            referenced.add(item1.id)
            referenced.add(item2.id)
    log.debug("adding addl pairs: %s" % ", ".join(["%s > %s" % (a.id, b.id) for a, b in addl_pairs]))
    pairs.extend(addl_pairs)

    # Check for reversed duplicates

    log.debug("before sort:\n" + "\n".join(["%s > %s" % (a.id, b.id) for a, b in pairs]))
    # Now perform the actual sort.
    result, has_cycle = topological_sort(pairs)
    if has_cycle:
        log.error('Indeterminate result; cycle in before/after sort for items %r', items)
    log.debug("after sort:\n" + "\n".join([a.id for a in result]))
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


def ranges_to_indexes(ranges):
    if len(ranges) == 0:
        return np.zeros([0], dtype=np.uint32)
    return np.hstack((np.arange(r[0], r[1], dtype=np.uint32) for r in ranges))


def indexes_to_ranges(indexes):
    groups = np.split(indexes, np.where(np.diff(indexes) != 1)[0] + 1)
    ranges = []
    for group in groups:
        if np.alen(group) > 0:
            ranges.append((int(group[0]), int(group[-1]) + 1))
    return ranges


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


def rect_ranges_to_indexes(row_width, start_offset, ranges):
    # Loop over each range to determine the indexes of the selected bytes
    # Returns a unique, monotonically increasing list of indexes to guarantee
    # that each index appears in the list only once.
    if len(ranges) == 0:
        return np.zeros([0], dtype=np.uint32)
    indexes = np.empty([0], dtype=np.uint32)
    log.debug("starting rects: %s" % np.vectorize(hex)(ranges))
    for start, end in ranges:
        if start is None:
            continue
        if start > end:
            start, end = end, start
        end -= 1  # instead of slice format, last byte becomes inclusive
        r1, c1 = divmod(start, row_width)
        r2, c2 = divmod(end, row_width)
        log.debug("before: %x-%x, (%d,%d) -> (%d,%d)" % (start, end, r1, c1, r2, c2))
        if c2 < c1:
            first_row_column_zero = start - c1
            c1, c2 = c2, c1
        else:
            first_row_column_zero = start - c1
        num_cols = c2 - c1 + 1
        num_rows = r2 - r1 + 1
        log.debug("range: %x-%x, (%d,%d) -> (%d,%d), nr=%d nc=%d zeroc=%x" % (start, end, r1, c1, r2, c2, num_rows, num_cols, first_row_column_zero))
        rect_indexes = np.hstack((np.arange(i + c1 + first_row_column_zero, i + c1 + first_row_column_zero + num_cols, dtype=np.uint32) for i in range(0, num_rows * row_width, row_width)))
        indexes = np.hstack((indexes, rect_indexes))

    unique_indexes = np.unique(indexes)
    log.debug("rect indexes: %s" % np.vectorize(hex)(unique_indexes))
    return unique_indexes


def invert_rects(rects, numr, numc):
    # Purely heuristic approach.  An algorithmic approach might be based on:
    # http://stackoverflow.com/questions/30818645 but this one breaks up the
    # entire space into a set of rectangles with boundaries at every possible
    # row/col boundary of all the contained rectangles.

    # Get list of all referenced rows and cols
    rows = sorted(list(set([r[0] for rect in rects for r in rect]).union(set([0, numr]))))
    cols = sorted(list(set([r[1] for rect in rects for r in rect]).union(set([0, numc]))))

    # create inside/outside flags for each row/col in the entire grid
    inside = np.zeros((numr, numc), dtype=np.bool_)
    for [(r1, c1), (r2, c2)] in rects:
        inside[r1:r2, c1:c2] = True

    # create lo/hi values for each subdivision of the grid
    rowpairs = [(rows[i], rows[i+1]) for i in range(len(rows) - 1)]
    colpairs = [(cols[i], cols[i+1]) for i in range(len(cols) - 1)]

    # create a rectangle at each intersection point and if it's outside the
    # original set of rectangles, add it to the list
    outside = []
    for r1, r2 in rowpairs:
        for c1, c2 in colpairs:
            if not inside[r1, c1]:
                outside.append([(r1, c1), (r2, c2)])

    # optimization: merge neighboring rectangles that share common edges

    return outside
