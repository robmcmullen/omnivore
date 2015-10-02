import numpy as np


class Document(object):
    def __init__(self, metadata, bytes):
        self.metadata = metadata
        self.bytes = np.fromstring(bytes, dtype=np.uint8)
    
    def __str__(self):
        return self.metadata.uri