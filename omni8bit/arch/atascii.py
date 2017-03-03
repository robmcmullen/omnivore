import numpy as np

atascii_to_internal = np.hstack([np.arange(64, 96, dtype=np.uint8),np.arange(64, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
atascii_to_internal = np.hstack([atascii_to_internal, atascii_to_internal + 128])

internal_to_atascii = np.hstack([np.arange(32, 96, dtype=np.uint8),np.arange(32, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
internal_to_atascii = np.hstack([internal_to_atascii, internal_to_atascii + 128])
