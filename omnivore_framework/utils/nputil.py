import numpy as np


def to_numpy(value):
    if type(value) is np.ndarray:
        return value
    elif type(value) is bytes:
        return np.fromstring(value, dtype=np.uint8)
    elif type(value) is list:
        return np.asarray(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")


def count_in_range(source_list, lowest_valid, highest_valid):
    """Count the number of items in the list between the lowest and highest
    values

    """
    npsource = np.asarray(source_list, dtype=np.uint32)
    count_low = len(np.where(npsource < lowest_valid)[0])
    count_high = len(np.where(npsource > highest_valid)[0])
    return count_low, count_high

# Fast integer-multiple scaling of bitmaps
def intscale(arr, hscale, wscale=None):
    if wscale is None:
        wscale = hscale
    hscale, wscale = int(hscale), int(wscale)
    h, w, depth = arr.shape
    if hscale == 1 and wscale == 1:
        return arr
    elif hscale < 1 or wscale < 1:
        raise ValueError("Scale must be an integer greater than 1")
    elif hscale == wscale:
        # some speedups for special cases where scale value is the same in both
        # directions
        if hscale == 2:
            output = np.empty((h * hscale, w * wscale, depth), dtype=np.uint8)
            # duplicate source pixels into two columns
            output[::2,::2,:] = arr[:,:,:]
            output[::2,1::2,:] = arr[:,:,:]
            # then copy completed rows to the row below
            output[1::2,:,:] = output[0::2,:,:]
            return output
        elif hscale == 3:
            output = np.empty((h * hscale, w * wscale, depth), dtype=np.uint8)
            # duplicate source pixels into three columns
            output[::3,::3,:] = arr[:,:,:]
            output[::3,1::3,:] = arr[:,:,:]
            output[::3,2::3,:] = arr[:,:,:]
            # then copy completed rows to the next two rows
            output[1::3,:,:] = output[::3,:,:]
            output[2::3,:,:] = output[::3,:,:]
            return output
        elif hscale == 4:
            output = np.empty((h * hscale, w * wscale, depth), dtype=np.uint8)
            # duplicate source pixels into four columns
            output[::4,0::4,:] = arr[:,:,:]
            output[::4,1::4,:] = arr[:,:,:]
            output[::4,2::4,:] = arr[:,:,:]
            output[::4,3::4,:] = arr[:,:,:]
            # copy completed rows to the next three rows
            output[1::4,:,:] = output[::4,:,:]
            output[2::4,:,:] = output[::4,:,:]
            output[3::4,:,:] = output[::4,:,:]
            return output
    output = np.empty((h * hscale, w * wscale, depth), dtype=np.uint8)
    # duplicate source pixels horizontally first onto the first line
    for i in range(wscale):
        output[::hscale,i::wscale,:] = arr[:,:,:]
    # duplicate lines to rows below them
    for i in range(1, hscale):
        output[i::hscale,:,:] = output[0::hscale,:,:]

    return output

# Fast integer-multiple scaling of bitmaps in the x direction
def intwscale(arr, scale):
    """Fast integer-multiple scaling of bitmaps.

    The scale is applied to both the width and height. Arrays are assumed to
    have the shape (height, width, depth)
    """
    scale = int(scale)
    if scale == 1:
        return arr
    elif scale < 1:
        raise ValueError("Scale must be an integer greater than 1")
    h, w, depth = arr.shape
    output = np.empty((h, w * scale, depth), dtype=np.uint8)
    if scale == 2:
        # duplicate source pixels into two columns
        output[::,0::2,:] = arr[:,:,:]
        output[::,1::2,:] = arr[:,:,:]
    elif scale == 3:
        # duplicate source pixels into three columns
        output[::,0::3,:] = arr[:,:,:]
        output[::,1::3,:] = arr[:,:,:]
        output[::,2::3,:] = arr[:,:,:]
    elif scale == 4:
        # duplicate source pixels into three columns
        output[::,0::4,:] = arr[:,:,:]
        output[::,1::4,:] = arr[:,:,:]
        output[::,2::4,:] = arr[:,:,:]
        output[::,3::4,:] = arr[:,:,:]
    else:
        raise ValueError("Scale greater than 4 not yet implemented")

    return output

def intwscale_font(arr, scale):
    """Fast integer-multiple scaling of font bitmaps.

    The scale is applied to both the width and height. Arrays are assumed to
    have the shape (num_glyphs, height, width, depth)
    """
    scale = int(scale)
    if scale == 1:
        return arr
    elif scale < 1:
        raise ValueError("Scale must be an integer greater than 1")
    num_glyphs, h, w, depth = arr.shape
    output = np.empty((num_glyphs, h, w * scale, depth), dtype=np.uint8)
    if scale == 2:
        # duplicate source pixels into two columns
        output[:,:,0::2,:] = arr[:,:,:,:]
        output[:,:,1::2,:] = arr[:,:,:,:]
    elif scale == 3:
        # duplicate source pixels into three columns
        output[:,:,0::3,:] = arr[:,:,:,:]
        output[:,:,1::3,:] = arr[:,:,:,:]
        output[:,:,2::3,:] = arr[:,:,:,:]
    elif scale == 4:
        # duplicate source pixels into three columns
        output[:,:,0::4,:] = arr[:,:,:,:]
        output[:,:,1::4,:] = arr[:,:,:,:]
        output[:,:,2::4,:] = arr[:,:,:,:]
        output[:,:,3::4,:] = arr[:,:,:,:]
    else:
        raise ValueError("Scale greater than 4 not yet implemented")

    return output
