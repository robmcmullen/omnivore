import os

from ..document import SawxDocument
from ..filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


class TextDocument(SawxDocument):
    def load_raw_data(self):
        fh = open(self.uri, 'r')
        return fh.read()

    def calc_raw_data(self, raw):
        return str(raw)

    def calc_raw_data_to_save(self):
        return self.raw_data

    def save_raw_data(self, uri, raw_data):
        fh = open(uri, 'w')
        log.debug("saving to %s" % uri)
        fh.write(raw_data)
        fh.close()

    # won't automatically match anything; must force this editor with the -t
    # command line flag
    @classmethod
    def can_load_file_exact(cls, file_metadata):
        return False

    @classmethod
    def can_load_file_generic(cls, file_metadata):
        return file_metadata['mime'].startswith("text/")
