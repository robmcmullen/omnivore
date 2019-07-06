import gzip
import io
import tarfile
import time

import numpy as np

from .. import errors
from ..archiver import Archiver

import logging
log = logging.getLogger(__name__)


class TarArchiver(Archiver):
    archive_type = "tar"

    def iter_archive(self, basename, byte_data):
        byte_data = io.BytesIO(byte_data)
        try:
            with tarfile.open(None, "r", byte_data) as zf:
                for item in zf.getmembers():
                    log.debug(f"tarinfo item: {item}")
                    item_data = np.frombuffer(zf.extractfile(item).read(), dtype=np.uint8)
                    yield item.name, item_data
        except:
            raise errors.InvalidArchiver("Not a tar file")

    def get_tarinfo(self, container):
        tarinfo = tarfile.TarInfo(container.pathname)
        tarinfo.mtime = time.time()
        tarinfo.uid = 400  # easter egg!
        tarinfo.gid = 800
        return tarinfo

    def pack_data(self, fh, containers, skip_missing_compressors=False):
        with tarfile.open(None, 'w', fh) as zf:
            for c in containers:
                byte_data = c.calc_packed_bytes(skip_missing_compressors)
                d = io.BytesIO(byte_data)
                tarinfo = self.get_tarinfo(c)
                tarinfo.size = len(byte_data)
                zf.addfile(tarinfo, d)
