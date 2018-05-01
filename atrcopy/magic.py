import numpy as np

import logging
log = logging.getLogger(__name__)


magic = [
    {'mime': "application/vnd.atari8bit.atr.getaway_pd",
     'name': "Getaway Public Domain ATR",
     'signature': [
         (slice(8, 10), [0x82, 0x39]),
         (slice(12, 16), [0x67, 0x21, 0x70, 0x64]),
         ],
    },

    {'mime': "application/vnd.atari8bit.xex.getaway",
     'name': "Getaway XEX",
     'signature': [
         (slice(0, 6), [0xff, 0xff, 0x80, 0x2a, 0xff, 0x8a]),
         ],
    },

    {'mime': "application/vnd.atari8bit.atr.getaway",
     'name': "Getaway ATR",
     'signature': [
         (slice(0x10, 0x19), [0x00, 0xc1, 0x80, 0x0f, 0xcc, 0x22, 0x18, 0x60, 0x0e]),
         ],
    },

    {'mime': "application/vnd.atari8bit.atr.jumpman_level_tester",
     'name': "Jumpman Level Tester from Omnivore",
     'signature': [
         (slice(0, 5), [0x96, 0x02 , 0xd0 , 0x05 , 0x80]),
         (0x0196 + 0x3f, 0x4c),
         (0x0196 + 0x48, 0x20),
         (0x0196 + 0x4b, 0x60),
         (0x0196 + 0x4c, 0xff),
         ],
    },

    {'mime': "application/vnd.atari8bit.atr.jumpman",
     'name': "Jumpman",
     'signature': [
         (slice(0, 5), [0x96, 0x02 , 0x80 , 0x16 , 0x80]),
         (0x0810 + 0x3f, 0x4c),
         (0x0810 + 0x48, 0x20),
         (0x0810 + 0x4b, 0x60),
         (0x0810 + 0x4c, 0xff),
         ],
    },
]


def check_signature(raw, sig):
    for index, expected in sig:
        actual = raw.data[index].tolist()
        if actual == expected:
            log.debug(" match at %s: %s" % (str(index), str(expected)))
        if actual != expected:
            log.debug(" failed at %s: %s != %s" % (str(index), str(expected), str(raw.data[index])))
            return False
    return True


def guess_detail_for_mime(mime, raw, parser):
    for entry in magic:
        if entry['mime'].startswith(mime):
            log.debug("checking signature for %s" % entry['mime'])
            if check_signature(raw, entry['signature']):
                log.debug("found signature: %s" % entry['name'])
                return entry['mime']
    return mime

