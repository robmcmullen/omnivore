def get_line(start_index, end_index, map_width):
    """Bresenham's Line Algorithm
    Produces a list of tuples from start and end
 
    >>> points1 = get_line((0, 0), (3, 4))
    >>> points2 = get_line((3, 4), (0, 0))
    >>> assert(set(points1) == set(points2))
    >>> print points1
    [(0, 0), (1, 1), (1, 2), (2, 3), (3, 4)]
    >>> print points2
    [(3, 4), (2, 3), (1, 2), (1, 1), (0, 0)]
    
    modified from:
    http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm
    """
    # Setup initial conditions
    y1, x1 = divmod(start_index, map_width)
    y2, x2 = divmod(end_index, map_width)
    dx = x2 - x1
    dy = y2 - y1

    # Determine how steep the line is
    is_steep = abs(dy) > abs(dx)

    # Rotate line
    if is_steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    # Swap start and end points if necessary and store swap state
    swapped = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        swapped = True

    # Recalculate differentials
    dx = x2 - x1
    dy = y2 - y1

    # Calculate error
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1

    # Iterate over bounding box generating points between start and end
    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = (y, x) if is_steep else (x, y)
        points.append(coord[1] * map_width + coord[0])
        error -= abs(dy)
        if error < 0:
            y += ystep
            error += dx

    # Reverse the list if the coordinates were swapped
    if swapped:
        points.reverse()
    return points


def get_bounds(start_index, end_index, map_width):
    y1, x1 = divmod(start_index, map_width)
    y2, x2 = divmod(end_index, map_width)

    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1), (x2, y2)


def get_rectangle(start_index, end_index, map_width):
    (x1, y1), (x2, y2) = get_bounds(start_index, end_index, map_width)

    points = []
    for x in range(x1, x2 + 1):
        points.append(y1 * map_width + x)
    for y in range(y1 + 1, y2):
        points.append(y * map_width + x1)
        if x2 > x1:
            points.append(y * map_width + x2)
    if y2 > y1:
        for x in range(x1, x2 + 1):
            points.append(y2 * map_width + x)
    return points


def get_filled_rectangle(start_index, end_index, map_width):
    (x1, y1), (x2, y2) = get_bounds(start_index, end_index, map_width)

    points = []
    for y in range(y1, y2 + 1):
        index = y * map_width + x1
        points.extend(list(range(index, index - x1 + x2 + 1)))
    return points
