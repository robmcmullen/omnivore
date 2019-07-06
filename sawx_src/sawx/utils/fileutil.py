import os
import glob
import shutil
import tempfile
import zipfile

import logging
log = logging.getLogger(__name__)


def get_latest_file(pathspec):
    files = glob.glob(pathspec)
    if files:
        # for f in files:
        #     print os.path.getctime(f), os.path.getmtime(f), f
        newest = max(files, key=os.path.getmtime)
        return newest
    return pathspec

class ExpandZip(object):
    """Expand a zip file to a temporary directory, creating a map from the name
    of the item in the archive to the pathname on disk.

    The temporary directory will be deleted when this object goes out of scope.
    """
    def __init__(self, archive_path_or_zipfile, skip_files=[]):
        if hasattr(archive_path_or_zipfile, 'infolist'):
            self.zf = self.already_opened_zf = archive_path_or_zipfile
            self.self_opened_zf = None
        else:
            self.zf = self.self_opened_zf = zipfile.ZipFile(archive_path_or_zipfile)
            self.already_opened_zf = None
        self.skip_files = skip_files
        self.root = tempfile.mkdtemp()
        self.name_map = {}
        self.expand()
        if self.self_opened_zf is not None:
            self.zf.close()
            self.self_opened_zf = None

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        log.debug("Removing temp directory %s" % self.root)
        shutil.rmtree(self.root, True)

    def expand(self):
        for info in self.zf.infolist():
            basename = os.path.basename(info.filename)
            if basename in self.skip_files:
                continue
            self.zf.extract(info, self.root)
            self.name_map[info.filename] = os.path.join(self.root, info.filename)

    def find_extension(self, ext):
        for pathname in self.name_map.values():
            if pathname.endswith(ext):
                return pathname
        else:
            raise OSError(f"No file ending in {ext} in archive")


def save_to_flat_zip(dest_filename, files):
    with open(dest_filename, "wb") as fh:
        zf = zipfile.ZipFile(fh, mode='w', compression=zipfile.ZIP_DEFLATED)
        for source in files:
            zf.write(source, os.path.basename(source), zipfile.ZIP_STORED)
        zf.close()
