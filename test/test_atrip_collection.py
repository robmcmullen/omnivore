import os
import glob

import numpy as np
import pytest
import jsonpickle

from mock import globbed_sample_atari_files, globbed_sample_atari_collections

from atrip.collection import Collection
from atrip.container import Container
from atrip.segment import Segment
import atrip.errors as errors


class TestCollection:
    def test_create(self):
        data = np.arange(4096, dtype=np.uint8)
        container = Container(data)
        collection = Collection("test", container=container)
        print(collection)
        assert collection.archiver.__class__.__name__ == "PlainFileArchiver"
        assert len(collection.containers) == 1
        assert len(collection.containers[0]) == 4096

    def test_serialize(self):
        filename = "dos_sd_test1.atr"
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        c = Collection(pathname)
        m = c.containers[0].media
        m.set_comment_at(100, "at location 100")
        m.set_comment_at(1000, "at location 1000")
        m.set_comment_at(10000, "at location 10000")
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
        m2 = c2.containers[0].media
        assert m2.get_comment_at(100) == "at location 100"
        assert m2.get_comment_at(1000) == "at location 1000"
        assert m2.get_comment_at(10000) == "at location 10000"
        c2.serialize_session(s2)
        j2 = jsonpickle.dumps(s2)
        assert j == j2

    @pytest.mark.parametrize(("pathname"), globbed_sample_atari_files)
    def test_single(self, pathname):
        collection = Collection(pathname)
        print(collection.verbose_info)
        output = "tmp." + os.path.basename(pathname)
        output = os.path.join(os.path.dirname(__file__), output)
        try:
            collection.save(output)
        except errors.InvalidAlgorithm as e:
            pytest.skip(f"skipping {pathname}: {e}")
        else:
            # compressed data may not be the same; don't really care as long as
            # it decompresses the same
            collection2 = Collection(output)
            print(collection.decompression_order)
            print(collection2.decompression_order)
            assert collection.decompression_order == collection2.decompression_order
            for c, c2 in zip(collection.containers, collection2.containers):
                print(f"checking collections: {c}, {c2}")
                assert np.array_equal(c._data, c2._data)

            if ".atr." in pathname or ".dcm." in pathname:
                if ".atr." in pathname:
                    ext = ".atr"
                else:
                    ext = ".dcm"
                orig, _ = pathname.split(ext + ".", 1)
                orig += ext
                collection_uncompressed = Collection(orig)
                print("comparing against uncompressed\n", collection_uncompressed.verbose_info)
                container_orig = collection.containers[0]
                container_uncompressed = collection_uncompressed.containers[0]
                assert np.array_equal(container_orig._data, container_uncompressed._data)

            if ".zip." in pathname or ".tar." in pathname:
                if ".zip." in pathname:
                    ext = ".zip"
                else:
                    ext = ".tar"
                orig, _ = pathname.split(ext + ".", 1)
                orig += ext
                collection_uncompressed = Collection(orig)
                print("comparing against uncompressed\n", collection_uncompressed.verbose_info)
                assert len(collection.containers) == len(collection_uncompressed.containers)
                for c, c2 in zip(collection.containers, collection_uncompressed.containers):
                    assert np.array_equal(c._data, c2._data)

    @pytest.mark.parametrize(("pathname"), globbed_sample_atari_collections)
    def test_multiple(self, pathname):
        self.test_single(pathname)

if __name__ == "__main__":
    t = TestCollection()
    # t.test_serialize()
    # t.test_single("../samples/mydos_sd_mydos4534.dcm.lz4")
    # t.test_single("../samples/dos_sd_test1.atr.gz")
    # t.test_single("../samples/dos_sd_test_collection.zip")
    # t.test_single("../samples/dos_sd_test_collection.tar")
    # t.test_single("../samples/dos_sd_test_collection.zip.lz4")
    t.test_create()
