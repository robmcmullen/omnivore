#!/usr/bin/env python

from atrutil import *

if __name__ == "__main__":
    import sys
    
    image = sys.argv[1]
    print image
    with open(image, "rb") as fh:
        atr = AtrDiskImage(fh)
        print atr
        for filename in sys.argv[2:]:
            print filename
            bytes = atr.find_file(filename)
            with open(filename, "wb") as fh:
                fh.write(bytes)
