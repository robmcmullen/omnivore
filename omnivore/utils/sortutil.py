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
        log.error('Indeterminate result; cycle in before/after sort for items %r', items)
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
    return np.hstack((np.arange(r[0], r[1], dtype=np.uint32) for r in ranges))

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
