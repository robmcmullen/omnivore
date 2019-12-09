#!/usr/bin/env python
import os
import glob
import json
import hashlib
import uuid

from PIL import Image
import numpy as np

import logging
log = logging.getLogger(__name__)


def bits_from_image(image):
    raw = image.tobytes()
    array = np.array(image)
    # print(array.shape)
    # print(array[:,16:32])

    line = np.empty((8, 1024), dtype=np.uint8)
    line[:,0:256] = array[0:8,0:256]
    line[:,256:512] = array[8:16,0:256]
    line[:,512:768] = array[16:24,0:256]
    line[:,768:1024] = array[24:32,0:256]

    # print(line.shape)
    # for i in range(32):
    #     print(line[:,8*i:8*i + 8])

    byte_array = np.packbits(line).reshape((8,128))
    # print(byte_array.shape)
    # for i in range(32):
    #     print(byte_array[:,i])
    return np.transpose(byte_array).copy()


if __name__ == "__main__":
    import sys

    source_dir = "../../Eightbit-Atari-Fonts/Original Bitmaps"
    template_dir = "../omnivore/templates"

    if len(sys.argv) > 1:
        # print out data for a particular font
        for font in sys.argv[1:]:
            filename = os.path.join(source_dir, font + ".png")
            im = Image.open(filename)
            data = bits_from_image(im)
            for i in range(128):
                row = data[i]
                print("        .byte " + ",".join([f"${a:02x}" for a in row]))
    else:
        for filename in sorted(glob.glob(source_dir + "/*")):
            name, _ = os.path.splitext(os.path.basename(filename))

            im = Image.open(filename)
            # print(im)

            data_bytes = bits_from_image(im)
            md5 = hashlib.md5(data_bytes).digest()
            new_uuid = str(uuid.UUID(bytes=md5))
            # print("md5", new_uuid)
            inf = {
                'uuid': new_uuid,
                'name': f"8x8 Atari 8-bit Font: {name}",
                'char_w': 8,
                'char_h': 8,
                'font_group': "Steve Boswell's Eightbit-Atari-Fonts",
            }

            basename = os.path.join(template_dir, str(new_uuid) + ".font")
            print(f"{name}: writing {basename}")
            with open(basename, 'wb') as fh:
                fh.write(data_bytes)
            with open(basename + ".inf", 'w') as fh:
                text = json.dumps(inf, indent=4, sort_keys=True) + "\n"
                fh.write(text)
