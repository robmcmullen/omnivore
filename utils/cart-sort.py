#!/usr/bin/env python
"""Sort cartridges by the result of guess_settings from the atari800
emulator. Running it like this:

    /home/rob/src/atari800/src/guess_settings -5200 -atari uncat/* >cart-info.txt

creates text output like this:

    uncat/Asteroids (USA) (Proto).a52: 5200    NTSC Atari   status: OK through 1000 frames (cart=19 'Standard 8 KB 5200')
    uncat/Asteroids (USA) (Proto).a52: 5200    NTSC Atari   status: FAIL (unidentified cartridge)
    uncat/Astro Chase (USA).a52: 5200    NTSC Atari   status: FAIL (BRK instruction) (cart=16 'One chip 16 KB 5200')
    uncat/Astro Chase (USA).a52: 5200    NTSC Atari   status: OK through 1000 frames (cart=6 'Two chip 16 KB 5200')
    uncat/Astro Chase (USA).a52: 5200    NTSC Atari   status: FAIL (unidentified cartridge)

Save that text file, and run this script with:

    python cart-sort dir/to/base/path cart-info.txt

and it will move carts to specific type directories based on the success or
failure shown in the output.
"""


import os
import sys


if __name__ == '__main__':
    base_dir = sys.argv[1]
    guess_settings = sys.argv[2]
    guess_settings = os.path.join(base_dir, guess_settings)
    try:
        with open(guess_settings, 'r') as fh:
            source_text = fh.read()
    except OSError:
        raise RuntimeError("Run guess_settings to generate list of working combinations")

    valid = {}
    for line in source_text.splitlines():
        if "status: OK" not in line:
            continue
        filename, extra = line.split(":", 1)
        if "cart=" not in extra:
            print(f"Error: {filename}: not a cartridge")
            continue
        _, num = extra.split("cart=", 1)
        num, _ = num.split(" ", 1)
        if filename not in valid:
            print(f"{filename}: cart-type = {num}")
            valid[filename] = num
        else:
            print(f"Warning: {filename}: cart-type = {num} already identified as cart-type = {valid[filename]}")
            continue

        subdir = os.path.join(base_dir, f"type{num}")
        try:
            os.mkdir(subdir)
        except FileExistsError:
            pass
        src = os.path.join(base_dir, filename)
        dest = os.path.join(subdir, os.path.basename(filename))
        print(f"{src} -> {dest}")
        os.rename(src, dest)


