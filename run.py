#!/usr/bin/env python

if __name__ == "__main__":
    import sys
    if sys.version_info < (3, 6, 0):
        print("atrip requires Python 3.6 or greater to run; this is Python %s" % ".".join([str(v) for v in sys.version_info[0:2]]))
    else:
        import atrip
    
        atrip.run()
