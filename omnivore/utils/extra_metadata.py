from segmentutil import DefaultSegment, AnticFontSegment, SegmentData
from omnivore.tasks.map_edit.pane_layout import task_id_with_pane_layout as map_edit_task_id

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
    print "HI!!!"
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

def check_builtin(doc):
    for match in [Getaway]:
        e = match(doc)
        if e is not None:
            return e
