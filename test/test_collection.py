import os
import glob

import numpy as np
import pytest
import jsonpickle

from mock import globbed_sample_atari_files

from atrip.collection import Collection
from atrip.segment import Segment
import atrip.errors as errors


class TestCollection:
    def test_serialize(self):
        filename = "dos_sd_test1.atr"
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        c = Collection(pathname)
        s = {}
        c.serialize_session(s)
        print(s)

        j = jsonpickle.dumps(s)
        print(j)
        
        sprime = jsonpickle.loads(j)
        jprime = jsonpickle.dumps(sprime)
        print(jprime)

        assert j == jprime

        c2 = Collection(pathname, session=sprime)
        s2 = {}
        c2.serialize_session(s2)
        j2 = jsonpickle.dumps(s2)
        assert j == j2

    @pytest.mark.parametrize(("pathname"), globbed_sample_atari_files)
    def test_glob(self, pathname):
        collection = Collection(pathname)
        print(collection.verbose_info)
        output = "tmp." + os.path.basename(pathname)
        output = os.path.join(os.path.dirname(__file__), output)
        try:
            collection.save(output)
        except errors.InvalidCompressor as e:
            pytest.skip(f"skipping {pathname}: {e}")
        else:
            # compressed data may not be the same; don't really care as long as
            # it decompresses the same
            collection2 = Collection(output)
            for c, c2 in zip(collection.containers, collection2.containers):
                print(f"checking collections: {c}, {c2}")
                assert np.array_equal(c._data, c2._data)

            if ".atr." in pathname:
                orig, _ = pathname.split(".atr.", 1)
                orig += ".atr"
                collection_uncompressed = Collection(orig)
                print("comparing against uncompressed\n", collection_uncompressed.verbose_info)
                container_orig = collection.containers[0]
                container_uncompressed = collection_uncompressed.containers[0]
                assert np.array_equal(container_orig._data, container_uncompressed._data)


if __name__ == "__main__":
    t = TestCollection()
    # t.test_serialize()
    # t.test_glob("../samples/mydos_sd_mydos4534.dcm.lz4")
    # t.test_glob("../samples/dos_sd_test1.atr.gz")
    # t.test_glob("../samples/dos_sd_test_collection.zip")
    t.test_glob("../samples/dos_sd_test_collection.tar")
