import numpy as np

from sawx.persistence import get_template


class JumpmanSaveAsATR(object):
    ##### Segment saver interface for menu item display

    export_data_name = "Jumpman Level Tester ATR"
    export_extensions = [".atr"]

    @classmethod
    def encode_data(cls, segment, editor):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        image = get_template("jumpman_level_tester.atr")
        if image is None:
            raise RuntimeError("Can't find Jumpman Level template file")
        raw = np.fromstring(image, dtype=np.uint8)
        raw[0x0196:0x0996] = segment[:]
        return raw.tobytes()


class JumpmanSaveAsXEX(object):
    ##### Segment saver interface for menu item display

    export_data_name = "Jumpman Level Tester XEX"
    export_extensions = [".xex"]

    @classmethod
    def encode_data(cls, segment, editor):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        image = get_template("jumpman_level_tester.atr")
        if image is None:
            raise RuntimeError("Can't find Jumpman Level template file")
        raw = np.fromstring(image, dtype=np.uint8)
        raw[0x0196:0x0996] = segment[:]

        # the level tester atr images is a KBoot image, so the XEX is embedded
        # inside it and we can just chop off the initial header
        xex = raw[0x0190:]
        return xex.tobytes()
