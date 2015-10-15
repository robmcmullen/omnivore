# Atari 8-bit utilities
import math

def clamp(val):
    if val < 0.0:
        return 0
    elif val > 255.0:
        return 255
    return int(val)

def ntsc_phase(cr):
    return ((cr-1)*25 - 58) * (2 * math.pi / 360);

def pal_phase(cr):
    return ((cr-1)*25.7 - 15) * (2 * math.pi / 360);

def gtia_to_rgb(val, phasefunc):
    # http://atariage.com/forums/topic/107853-need-the-256-colors/page-2#entry1312467
    cr = (val >> 4) & 15;
    lm = val & 15;
    if cr > 0:
        crlv = 50
    else:
        crlv = 0

    phase = phasefunc(cr)

    y = 255*(lm+1)/16;
    i = crlv*math.cos(phase);
    q = crlv*math.sin(phase);

    r = y + 0.956*i + 0.621*q;
    g = y - 0.272*i - 0.647*q;
    b = y - 1.107*i + 1.704*q;

    return clamp(r), clamp(g), clamp(b)

def gtia_ntsc_to_rgb(val):
    return gtia_to_rgb(val, ntsc_phase)

def gtia_pal_to_rgb(val):
    return gtia_to_rgb(val, pal_phase)

def atari_color_to_rgb(val, country="NTSC"):
    if country == "PAL":
        return gtia_pal_to_rgb(val)
    return gtia_ntsc_to_rgb(val)

def powerup_colors():
    # From Mapping the Atari
    return list([40, 202, 148, 70, 0])

def gr0_colors(colors):
    bg = colors[2]
    cr = bg & 0xf0;
    lm = colors[1] & 0x0f
    fg = cr | lm
    return fg, bg

# Don't export the utility functions 
__all__ = ['atari_color_to_rgb', 'powerup_colors', 'gr0_colors']


if __name__ == "__main__":
    for i in range(33):
        print i, gtia_ntsc_to_rgb(i), gtia_pal_to_rgb(i)
