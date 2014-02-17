from pyface.tasks.topological_sort import topological_sort

def before_after_wildcard_sort(items):
    """ Sort a sequence of items with 'before', 'after', and 'id' attributes.
        
    The sort is topological. If an item does not specify a 'before' or 'after',
    it is placed after the preceding item.

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
            parent, child = item, item_map.get(item.before)
            if child:
                new_pairs.append((parent, child))
        if hasattr(item, 'after') and item.after:
            parent, child = item_map.get(item.after), item
            if parent:
                new_pairs.append((parent, child))

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
