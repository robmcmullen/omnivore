# Fast integer multiple scaling of bitmaps

import numpy as np

def intscale(arr, scale, output=None):
    scale = int(scale)
    if scale == 1:
        return arr
    elif scale < 1:
        raise ValueError("Scale must be an integer greater than 1")
    h, w, depth = arr.shape
    if output is None:
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
    else:
        raise ValueError("Scale greater than 3 not yet implemented")
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
