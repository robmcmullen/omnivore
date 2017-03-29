import numpy as np

def count_in_range(source_list, lowest_valid, highest_valid):
    """Count the number of items in the list between the lowest and highest
    values

    """
    npsource = np.asarray(source_list, dtype=np.uint32)
    count_low = len(np.where(npsource < lowest_valid)[0])
    count_high = len(np.where(npsource > highest_valid)[0])
    return count_low, count_high
