from segmentutil import DefaultSegment, AnticFontSegment, SegmentData
from omnivore.tasks.map_edit.pane_layout import task_id_with_pane_layout as map_edit_task_id
from omnivore.tasks.jumpman.pane_layout import task_id_with_pane_layout as jumpman_task_id

getaway_defaults = {
    'colors': [0x46, 0xD6, 0x74, 0x0C, 0x14, 0x86, 0x02, 0xB6, 0xBA],
    'tile map': [
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
        ]
    }

def Getaway(doc):
    state = doc.bytes[0:6] == [0xff, 0xff, 0x80, 0x2a, 0xff, 0x8a]
    if state.all():
        print "Found getaway.xex!!!"
        r = doc.segments[0].rawdata
        font_segment = AnticFontSegment(r[0x086:0x486], 0x2b00, name="Playfield font")
        #doc.add_user_segment(font_segment)
        segment = DefaultSegment(r[0x2086:0x6086], 0x4b00, name="Playfield map")
        segment.map_width = 256
        #doc.add_user_segment(segment)
        extra_metadata = {
            'font': (font_segment.antic_font, 5),
            'user segments': [font_segment, segment],
            'initial segment': segment,
            }
        extra_metadata.update(getaway_defaults)
        doc.last_task_id = map_edit_task_id
        return extra_metadata
    
    state = doc.bytes[0x10:0x19] == [0x00, 0xc1, 0x80, 0x0f, 0xcc, 0x22, 0x18, 0x60, 0x0e]
    if state.all():
        print "Found getaway.atr!!!"
        r = doc.segments[0].rawdata
        font_segment = AnticFontSegment(r[0x090:0x490], 0x2b00, name="Playfield font")
        #doc.add_user_segment(font_segment)
        segment = DefaultSegment(r[0x2090:0x6090], 0x4b00, name="Playfield map")
        segment.map_width = 256
        #doc.add_user_segment(segment)
        extra_metadata = {
            'font': (font_segment.antic_font, 5),
            'user segments': [font_segment, segment],
            'initial segment': segment,
            }
        extra_metadata.update(getaway_defaults)
        doc.last_task_id = map_edit_task_id
        return extra_metadata

def JumpmanLevelBuilder(doc):
    state = doc.bytes[0:5] == [0x96, 0x02 , 0xd0 , 0x05 , 0x80]
    if not state.all():
        return
    # Check invariant bytes in the level data to make sure
    s = doc.bytes[0x0196:0x0296]
    if s[0x3f] == 0x4c and s[0x48] == 0x20 and s[0x4b] == 0x60 and s[0x4c] == 0xff:
        print "Found jumpman level builder!!!"
        r = doc.segments[0].rawdata
        found_level = False
        user_segments = []
        for s in doc.segments:
            if s.start_addr == 0x2800 and len(s) == 0x800:
                found_level = True
        if not found_level:
            user_segments.append(DefaultSegment(r[0x0196:0x0996], 0x2800, name="Jumpman Level Data"))
            user_segments.append(DefaultSegment(r[2458:3994], 0x0a00, name="Code at $0a00"))
            user_segments.append(DefaultSegment(r[3998:6046], 0x2000, name="Code at $2000"))
            user_segments.append(DefaultSegment(r[6050:22434], 0x3000, name="Code at $3000"))
        extra_metadata = {
            'user segments': user_segments,
            'initial segment': user_segments[0],
            }
        doc.last_task_id = jumpman_task_id
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
        print "Found jumpman ATR!!!"
        r = doc.segments[0].rawdata
        found_level = False
        user_segments = []
        start = 0x0810
        for i in range(32):
            user_segments.append(DefaultSegment(r[start:start+0x800], 0x2800, name=level_names[i]))
            start += 0x800
        user_segments.append(DefaultSegment(r[70032:71568], 0x0a00, name="Code"))
        user_segments.append(DefaultSegment(r[71568:92048], 0x2000, name="Code"))
        extra_metadata = {
            'user segments': user_segments,
            'initial segment': user_segments[0],
            }
        doc.last_task_id = jumpman_task_id
        return extra_metadata

def check_builtin(doc):
    for match in [Getaway, JumpmanLevelBuilder, JumpmanFullAtr]:
        e = match(doc)
        if e is not None:
            return e
    return dict()
