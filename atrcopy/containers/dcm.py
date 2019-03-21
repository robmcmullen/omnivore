from .. import errors


name = "dcm"

valid_densities = {
    0: (720, 128),
    1: (720, 256),
    2: (1040, 128),
}


def unpack_bytes(data):
    index = 0
    count = len(data)
    raw = data

    def get_next():
        nonlocal index, raw

        try:
            data = raw[index]
        except IndexError:
            raise errors.InvalidContainer("Incomplete DCM file")
        else:
            index += 1
        return data

    archive_type = get_next()
    if archive_type == 0xf9 or archive_type == 0xfa:
        archive_flags = get_next()
        if archive_flags & 0x1f != 1:
            if archive_type == 0xf9:
                raise errors.InvalidContainer("DCM multi-file archive combined in the wrong order")
            else:
                raise errors.InvalidContainer("Expected pass one of DCM archive first")
        density_flag = (archive_flags >> 5) & 3
        if density_flag not in valid_densities:
            raise errors.InvalidContainer(f"Unsupported density flag {density_flag} in DCM")
    else:
        raise errors.InvalidContainer("Not a DCM file")

    # DCM decoding goes here. Currently, instead of decoding it raises the
    # UnsupportedContainer exception, which signals to the caller that the
    # container has been successfully identified but can't be parsed.
    #
    # When decoding is supported, return the decoded byte array instead of
    # this exception.
    raise errors.UnsupportedContainer("DCM archives are not yet supported")


def pack_bytes(media_container):
    """Pack the container using this packing algorithm

    Return a byte string suitable to be written to disk
    """
    raise NotImplementedError
