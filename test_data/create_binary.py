#!/usr/bin/env python
"""

"""

import os
import numpy as np
import subprocess
import tempfile

def create_binary(filename, num, outfile, options):
    """Create patterned binary data with the first 7 characters of the filename
    interleaved with a byte ramp, e.g.  A128   \x00A128   \x01A128   \x02 etc.
    """
    root, _ = outfile.split(".")
    prefix = ("%s        " % root)[0:8]
    a = np.fromstring(prefix, dtype=np.uint8)
    b = np.tile(a, (num / np.alen(a)) + 1)[0:num]
    b[7::8] = np.arange(np.alen(b) / 8, dtype=np.uint8)
    with open(filename, "wb") as fh:
        fh.write(b.tostring())

def num_to_letter(num):
    text = []
    while True:
        num, rem = divmod(num, 26)
        text[0:0] = chr(ord("A") + rem)
        if num == 0:
            break
    return "".join(text)

def get_filename(num, used):
    if num not in used:
        used[num] = 0
    prefix = num_to_letter(used[num])
    filename = "%s%d.DAT" % (prefix, num)
    used[num] += 1
    return filename

def franny(filename, *options):
    cmd = ["franny", filename]
    cmd.extend(options)
    msg = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images off ATR format disks")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("-p", "--prefix", default="B", action="store")
    parser.add_argument("-f", "--filesystem", default="a", action="store")
    parser.add_argument("-d", "--density", default="s", action="store")
    parser.add_argument("-s", "--sectors", default=720, type=int, action="store")
    parser.add_argument("-t", "--template", default="", action="store")
    parser.add_argument("-o", "--output", default="a.out", action="store")
    parser.add_argument("files", metavar="NUM", nargs="+", help="list of numbers specifying the size of each binary file")
    options, extra_args = parser.parse_known_args()
    
    out = options.output
    if options.template:
        franny(out, "-C", "-f", options.filesystem, "-t", options.template)
    else:
        franny(out, "-C", "-f", options.filesystem, "-d", options.density, "-s", str(options.sectors))
    fh, binfile = tempfile.mkstemp()
    os.close(fh)
    used = {}
    files = []
    print "Creating image %s" % out
    for entry in options.files:
        entry = entry.lower()
        if entry.startswith("d"):
            index = int(entry[1:])
            outfile = files[index]
            franny(out, "-U", outfile)
        else:
            if "*" in entry:
                repeat, num = entry.split("*", 1)
                num = int(num)
                repeat = int(repeat)
                entries = [num] * repeat
            elif "-" in entry:
                first, last = entry.split("-", 1)
                first = int(first)
                if "," in last:
                    last, step = last.split(",", 1)
                    step = int(step)
                else:
                    step = 1
                last = int(last)
                entries = range(first, last + 1, step)
            else:
                num = int(entry)
                entries = [num]
            for i in entries:
                outfile = get_filename(i, used)
                create_binary(binfile, i, outfile, options)
                franny(out, "-A", "-i", binfile, "-o", outfile)
                files.append(outfile)
    os.unlink(binfile)
