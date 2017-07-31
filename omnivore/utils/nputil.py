import numpy as np

def count_in_range(source_list, lowest_valid, highest_valid):
    """Count the number of items in the list between the lowest and highest
    values

    """
    npsource = np.asarray(source_list, dtype=np.uint32)
    count_low = len(np.where(npsource < lowest_valid)[0])
    count_high = len(np.where(npsource > highest_valid)[0])
    return count_low, count_high

# Fast integer-multiple scaling of bitmaps
def intscale(arr, scale):
    scale = int(scale)
    if scale == 1:
        return arr
    elif scale < 1:
        raise ValueError("Scale must be an integer greater than 1")
    h, w, depth = arr.shape
    output = np.empty((h * scale, w * scale, depth), dtype=np.uint8)
    dest_h = scale * h
    dest_w = scale * w
    if scale == 2:
        # duplicate source pixels into two columns
        output[::2,::2,:] = arr[:,:,:]
        output[::2,1::2,:] = arr[:,:,:]
        # then copy completed rows to the row below
        output[1::2,:,:] = output[0::2,:,:]
    elif scale == 3:
        # duplicate source pixels into three columns
        output[::3,::3,:] = arr[:,:,:]
        output[::3,1::3,:] = arr[:,:,:]
        output[::3,2::3,:] = arr[:,:,:]
        # then copy completed rows to the next two rows
        output[1::3,:,:] = output[::3,:,:]
        output[2::3,:,:] = output[::3,:,:]
    elif wscale == 4:
        # duplicate source pixels into four columns
        output[::4,0::4,:] = arr[:,:,:]
        output[::4,1::4,:] = arr[:,:,:]
        output[::4,2::4,:] = arr[:,:,:]
        output[::4,3::4,:] = arr[:,:,:]
        # copy completed rows to the next three rows
        output[1::4,:,:] = output[::4,:,:]
        output[2::4,:,:] = output[::4,:,:]
        output[2::4,:,:] = output[::4,:,:]
    else:
        raise ValueError("Scale greater than 4 not yet implemented")
        for y in range(h):
            dest_y = y * 3
            # duplicate source pixels to three columns
            output[dest_y,::3,:] = arr[y,::,:]
            output[dest_y,1::3,:] = arr[y,::,:]
            output[dest_y,2::3,:] = arr[y,::,:]
            # then copy that row to two more
            output[dest_y+1,:,:] = output[dest_y,:,:]
            output[dest_y+2,:,:] = output[dest_y,:,:]

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
