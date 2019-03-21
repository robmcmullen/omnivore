import bz2
import io

from .. import errors


name = "bzip"

def unpack_bytes(byte_data):
    try:
        buf = io.BytesIO(byte_data)
        with bz2.BZ2File(buf, mode='rb') as f:
            unpacked = f.read()
    except OSError as e:
        raise errors.InvalidContainer(e)
    return unpacked


def pack_bytes(media_container):
    """Pack the container using this packing algorithm

    Return a byte string suitable to be written to disk
    """
    raise NotImplementedError
