from atrcopy import DefaultSegment

from ..utils.segmentutil import AnticFontSegment

import logging
log = logging.getLogger(__name__)

getaway_machine_defaults = {
    'antic_color_registers': [0x46, 0xD6, 0x74, 0x0C, 0x14, 0x86, 0x02, 0xB6, 0xBA],
    'font_renderer': 2,  # "Antic 5",
    'font_mapping': 1,  # "Antic Order",
    }

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
    'last_task_id': 'byte_edit',
    'layout': 'map',
    'uuid': 'default',
    }

supported_pd_getaway = [1]

def getaway_metadata(font_segment, segment):
    m = dict(getaway_machine_defaults)
    m['antic_font_data'] = font_segment.antic_font
    extra_metadata = {
        'machine': m,
        'user segments': [font_segment, segment],
        'initial segment': segment.name,
    }
    extra_metadata.update(getaway_defaults)
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
        r = doc.segments[0].rawdata
        found_level = False
        user_segments = []
        for s in doc.segments:
            if s.start_addr == 0x2800 and len(s) == 0x800:
                found_level = True
                initial_segment = s
        if not found_level:
            user_segments.append(DefaultSegment(r[0x0196:0x0996], 0x2800, name="Jumpman Level Data"))
            user_segments.append(DefaultSegment(r[2458:3994], 0x0a00, name="Code at $0a00"))
            user_segments.append(DefaultSegment(r[3998:6046], 0x2000, name="Code at $2000"))
            user_segments.append(DefaultSegment(r[6050:22434], 0x3000, name="Code at $3000"))
            initial_segment = user_segments[0]
        log.debug("Found initial segment: %s, %s" % (initial_segment, initial_segment.uuid))
        extra_metadata = {
            'user segments': user_segments,
            'initial segment': initial_segment.name,
            'last_task_id': 'byte_edit',
            'layout': 'jumpman',
            }
        return extra_metadata


level_names = [
    "01: easy does it",
    "02: robots I",
    "03: bombs away",
    "04: jumping blocks",
    "05: vampire",
    "06: invasion",
    "07: GP I",
    "08: builder",
    "09: look out below",
    "10: hotfoot",
    "11: runaway",
    "12: robots II",
    "13: hailstones",
    "14: dragonslayer",
    "15: GP II",
    "16: ride around",
    "17: roost",
    "18: roll me over",
    "19: ladder challenge",
    "20: figureit",
    "21: jump n run",
    "22: freeze",
    "23: follow the leader",
    "24: the jungle",
    "25a: mystery maze #1",
    "25b: mystery maze #2",
    "25c: mystery maze #3",
    "26: gunfighter",
    "27: robots III",
    "28: now you see it",
    "29: going down",
    "30: GP III",
]


def JumpmanFullAtr(doc):
    state = doc.bytes[0:5] == [0x96, 0x02 , 0x80 , 0x16 , 0x80]
    if not state.all():
        return
    # Check invariant bytes in the level data to make sure
    s = doc.bytes[0x0810:0x0910]
    if s[0x3f] == 0x4c and s[0x48] == 0x20 and s[0x4b] == 0x60 and s[0x4c] == 0xff:
        log.debug("Found jumpman ATR!!!")
        r = doc.segments[0].rawdata
        found_level = False
        user_segments = []
        start = 0x0810
        for i in range(32):
            s = DefaultSegment(r[start:start+0x800], 0x2800, name=level_names[i])
            if not doc.find_matching_segment(s):
                log.debug("adding %s" % s)
                user_segments.append(s)
            start += 0x800
        for s in [DefaultSegment(r[70032:71568], 0x0a00, name="Code"), DefaultSegment(r[71568:92048], 0x2000, name="Code")]:
            if not doc.find_matching_segment(s):
                log.debug("adding %s" % s)
                user_segments.append(s)

        extra_metadata = {
            'user segments': user_segments,
            'initial segment': user_segments[0].name,
            'last_task_id': 'byte_edit',
            'layout': 'jumpman',
            }
        return extra_metadata


def check_builtin(doc):
    if len(doc.bytes) > 0:
        for match in [Getaway, JumpmanLevelBuilder, JumpmanFullAtr]:
            log.debug("Checking for builtin metadata: %s" % (match.__name__))
            e = match(doc)
            if e is not None:
                return e
    return dict()
