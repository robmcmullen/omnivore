import gzip
import io

from .. import errors


name = "gzip"

def unpack_bytes(byte_data):
    try:
        buf = io.BytesIO(byte_data)
        with gzip.GzipFile(mode='rb', fileobj=buf) as f:
            unpacked = f.read()
    except OSError as e:
        raise errors.InvalidContainer(e)
    return unpacked


def pack_bytes(media_container):
    """Pack the container using this packing algorithm

    Return a byte string suitable to be written to disk
    """
    raise NotImplementedError
