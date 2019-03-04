import sys

import gc

def find_referrers_of_class(cls):
    gc.collect()
    obj_list = []
    count = 0

    def namestr(obj, namespace):
        return [name for name in namespace if namespace[name] is obj]            
    for obj in gc.get_objects():
        if isinstance(obj, cls):
            print(("Found: %s" % str(obj)))
            rlist = gc.get_referrers(obj)
            print(("  Referenced by: %d" % len(rlist)))
            for r in rlist:
                # print("  * refobj of %s: %s %s" % (obj.__class__.__name__, type(r), namestr(r, globals())))
                print(("  * refobj of %s: %s %s" % (obj.__class__.__name__, type(r), str(r))))
        else:
            count += 1
    print(("%d total objects" % count))
