from atrcopy import DefaultSegment

from ..utils.segmentutil import AnticFontSegment

import logging
log = logging.getLogger(__name__)


getaway_defaults = {
    'tile groups': [
        ("road", [0x70]),
        ("trees", range(0x80, 0x96), range(0x01, 0x16),),
        ("buildings", range(0x96, 0x9f), range(0x16, 0x1f), range(0x41, 0x51), range(0x5d, 0x60),),
        ("people", range(0xf1, 0xf4), range(0x71, 0x74)),
        ("water", range(0x2e, 0x41),),
        ("bridges", range(0x69, 0x6d),),
        ("vehicles", range(0x51, 0x59),),
        ("airport", range(0x60, 0x68), [0x5f], range(0x59, 0x5d), range(0xd9, 0xdd)),
        ("golf", range(0xa9, 0xae),),
        ("other", [0x20, 0x25, 0x26, ]),
        ("special", range(0x21, 0x25), range(0x74, 0x76),),
        ],
    'uuid': 'default',
    }

supported_pd_getaway = [1]

def getaway_metadata(font_segment, segment):
    extra_metadata = {
        'last_task_id': 'omnivore.byte_edit',
        'omnivore.byte_edit': {
            'viewers' : [
                {
                    'name': 'map',
                    'uuid': 'uuid-getaway',
                    'linked base': 'default',
                    'control': {'items_per_row': 256, 'zoom': 2},
                    'machine': {
                        'antic_color_registers': [0x46, 0xD6, 0x74, 0x0C, 0x14, 0x86, 0x02, 0xB6, 0xBA],
                        'antic_font_data': font_segment.antic_font,
                        'font_renderer': 2,  # "Antic 5",
                        'font_mapping': 1,  # "Antic Order",
                        },
                },
            ],
            'initial segment': segment.name,
        },
        'user segments': [font_segment, segment],
    }
    return extra_metadata

def Getaway(doc):
    if doc.bytes[8] == 0x82 and doc.bytes[9] == 0x39:
        state = doc.bytes[12:16] == [0x67, 0x21, 0x70, 0x64]
        if state.all():
            log.debug("Found Omnivore-enabled public domain getaway.xex!!!")
            version = doc.bytes[16]
            num_words = doc.bytes[17]
            words = doc.bytes[18:18 + num_words * 2].copy().view(dtype='<u2')
            r = doc.segments[0].rawdata
            if version in supported_pd_getaway:
                log.debug("Found supported version %d" % version)
            else:
                latest = reduce(max, supported_pd_getaway)
                log.debug("Unsupported version %d; trying latest %d" % (version, latest))
                version = latest
            playfield = words[0]
            playfield_font = words[1]
            log.debug("playfield address: %04x, font address: %04x" % (playfield, playfield_font))
            log.debug(doc)
            segments = doc.find_segments_in_range(playfield)
            if not segments:
                log.error("playfield not found at %04x in any segment" % playfield)
                return
            _, s, _ = segments[0]
            i = s.get_raw_index_from_address(playfield)
            segment = DefaultSegment(r[i:i + 0x4000], playfield, name="Playfield map")
            segment.map_width = 256

            segments = doc.find_segments_in_range(playfield_font)
            if not segments:
                log.error("playfield font not found at %04x in any segment" % playfield_font)
                return
            _, s, _ = segments[0]
            i = s.get_raw_index_from_address(playfield_font)
            font_segment = AnticFontSegment(r[i:i + 0x400], playfield_font, name="Playfield font")

            return getaway_metadata(font_segment, segment)

    state = doc.bytes[0:6] == [0xff, 0xff, 0x80, 0x2a, 0xff, 0x8a]
    if state.all():
        log.debug("Found getaway.xex!!!")
        r = doc.segments[0].rawdata
        font_segment = AnticFontSegment(r[0x086:0x486], 0x2b00, name="Playfield font")
        #doc.add_user_segment(font_segment)
        segment = DefaultSegment(r[0x2086:0x6086], 0x4b00, name="Playfield map")
        segment.map_width = 256
        #doc.add_user_segment(segment)
        return getaway_metadata(font_segment, segment)

    state = doc.bytes[0x10:0x19] == [0x00, 0xc1, 0x80, 0x0f, 0xcc, 0x22, 0x18, 0x60, 0x0e]
    if state.all():
        log.debug("Found getaway.atr!!!")
        r = doc.segments[0].rawdata
        font_segment = AnticFontSegment(r[0x090:0x490], 0x2b00, name="Playfield font")
        #doc.add_user_segment(font_segment)
        segment = DefaultSegment(r[0x2090:0x6090], 0x4b00, name="Playfield map")
        segment.map_width = 256
        #doc.add_user_segment(segment)
        return getaway_metadata(font_segment, segment)


def JumpmanLevelBuilder(doc):
    state = doc.bytes[0:5] == [0x96, 0x02 , 0xd0 , 0x05 , 0x80]
    if not state.all():
        return
    # Check invariant bytes in the level data to make sure
    s = doc.bytes[0x0196:0x0296]
    if s[0x3f] == 0x4c and s[0x48] == 0x20 and s[0x4b] == 0x60 and s[0x4c] == 0xff:
        log.debug("Found jumpman level builder!!!")
        extra_metadata = doc.calc_unserialized_template('vnd.atari8bit.atr.jumpman_level_tester')
        extra_metadata['omnivore.byte_edit']['initial segment'] = extra_metadata['serialized user segments'][0].name
        return extra_metadata


def JumpmanFullAtr(doc):
    state = doc.bytes[0:5] == [0x96, 0x02 , 0x80 , 0x16 , 0x80]
    if not state.all():
        return
    # Check invariant bytes in the level data to make sure
    s = doc.bytes[0x0810:0x0910]
    if s[0x3f] == 0x4c and s[0x48] == 0x20 and s[0x4b] == 0x60 and s[0x4c] == 0xff:
        log.debug("Found jumpman ATR!!!")
        extra_metadata = doc.calc_unserialized_template('vnd.atari8bit.atr.jumpman')
        extra_metadata['omnivore.byte_edit']['initial segment'] = extra_metadata['serialized user segments'][0].name
        return extra_metadata


def check_builtin(doc):
    if len(doc.bytes) > 0:
        for match in [Getaway, JumpmanLevelBuilder, JumpmanFullAtr]:
            log.debug("Checking for builtin metadata: %s" % (match.__name__))
            e = match(doc)
            if e is not None:
                return e
    return dict()
