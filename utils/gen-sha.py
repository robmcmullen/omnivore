#!/usr/bin/env python
import os
import sys
import hashlib
from collections import defaultdict
import pprint

import slugify

def parse(filename, mime):
    data = open(filename, 'rb').read()
    h = hashlib.sha1(data).digest()
    name = os.path.basename(os.path.splitext(filename)[0])
    return len(data), h, name



if __name__ == '__main__':
    this_dir = os.getcwd()
    source_dir = os.path.join(this_dir, "..", "atrip/signatures/")
    mime_with_type = sys.argv[1]
    if ".type" in mime_with_type:
        mime, _ = mime_with_type.rsplit(".type", 1)
    else:
        mime = mime_with_type
    slug = slugify.slugify(mime.replace("application/x.", ""), separator="_")
    source = os.path.join(source_dir, slug) + ".py"
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
    new_signatures = defaultdict(dict)
    new_signatures.update(sha1_signatures)
    for filename in sys.argv[2:]:
        print(f"parsing {filename}")
        size, hash_string, name = parse(filename, mime)
        _, rem = divmod(size, 1024)
        if rem > 0:
            print(f"skipping {name}; not a ROM image size")
            continue
        print(f"{size} {hash_string} {name}")
        new_signatures[mime_with_type][hash_string] = name
    lines = []
    lines.append("sha1_signatures = {")
    for k,v in sorted(new_signatures.items()):
        lines.append(f"\"{k}\": {{")
        for h,n in sorted(v.items(), key=lambda a:(a[1], a[0])):
            lines.append(f"  {h}: {repr(n)},")
        lines.append("},")
    lines.append("}  # end sha1_signatures\n")

    print("\n".join(lines))
    with open(source, 'w') as fh:
        fh.write("\n".join(lines))