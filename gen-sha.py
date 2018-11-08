#!/usr/bin/env python
import os
import sys
import hashlib
from collections import defaultdict
import pprint

def parse(filename, mime):
    data = open(filename, 'rb').read()
    h = hashlib.sha1(data).hexdigest()
    name = os.path.basename(os.path.splitext(filename)[0])
    return len(data), h, name



if __name__ == '__main__':
    source = "atrcopy/signatures.py"
    try:
        with open(source, 'r') as fh:
            source_text = fh.read()
    except OSError:
        source_text = "sha1_signatures = {}"
    try:
        exec(source_text)
    except:
        raise
    print(sha1_signatures)
    mime = sys.argv[1]
    new_signatures = defaultdict(dict)
    new_signatures.update(sha1_signatures)
    for filename in sys.argv[2:]:
        print(f"parsing {filename}")
        size, hash_string, name = parse(filename, mime)
        print(f"{size} {hash_string} {mime} {name}")
        new_signatures[size][hash_string] = (mime, name)
    lines = []
    lines.append("sha1_signatures = {")
    for k,v in sorted(new_signatures.items()):
        lines.append(f"{k}: {{")
        for h,n in sorted(v.items(), key=lambda a:(a[1], a[0])):
            lines.append(f"  '{h}': {n},")
        lines.append("},")
    lines.append("}  # end sha1_signatures")

    print("\n".join(lines))
    with open(source, 'w') as fh:
        fh.write("\n".join(lines))