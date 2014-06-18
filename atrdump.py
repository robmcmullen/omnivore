#!/usr/bin/env python

from atrutil import *

if __name__ == "__main__":
    import sys
    
    for args in sys.argv:
        print args
        with open(args, "rb") as fh:
            atr = AtrDiskImage(fh)
            print atr
            for dirent in atr.files:
                bytes = atr.get_file(dirent)
                filename = dirent.get_filename()
                with open(filename, "wb") as fh:
                    fh.write(bytes)

