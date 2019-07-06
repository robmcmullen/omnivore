import numpy as np

import logging
log = logging.getLogger(__name__)


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
