# Atari 8-bit utilities
import math

# Color references:
#
# Color swatches http://atariage.com/forums/topic/243369-atari-128-color-palettes/

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

ntsc_iq_lookup = [
    [  0.000,  0.000 ],
    [  0.144, -0.189 ],
    [  0.231, -0.081 ],
    [  0.243,  0.032 ],
    [  0.217,  0.121 ],
    [  0.117,  0.216 ],
    [  0.021,  0.233 ],
    [ -0.066,  0.196 ],
    [ -0.139,  0.134 ],
    [ -0.182,  0.062 ],
    [ -0.175, -0.022 ],
    [ -0.136, -0.100 ],
    [ -0.069, -0.150 ],
    [  0.005, -0.159 ],
    [  0.071, -0.125 ],
    [  0.124, -0.089 ],
    ]

def gtia_ntsc_to_rgb_table(val):
    # This is a better representation of the NTSC colors using a lookup table
    # rather than the phase calculations. Also from the same thread:
    # http://atariage.com/forums/topic/107853-need-the-256-colors/page-2#entry1319398
    cr = (val >> 4) & 15;
    lm = val & 15;

    y = 255*(lm+1)/16;
    i = ntsc_iq_lookup[cr][0] * 255
    q = ntsc_iq_lookup[cr][1] * 255

    r = y + 0.956*i + 0.621*q;
    g = y - 0.272*i - 0.647*q;
    b = y - 1.107*i + 1.704*q;

    return clamp(r), clamp(g), clamp(b)

gtia_ntsc_to_rgb = gtia_ntsc_to_rgb_table

def powerup_colors():
    # Playfield colors are from Mapping the Atari
    # Player/missile colors (the first 4 colors) are normally zero, but I'm
    # specifying others here so they are distinguishable when used.
    return list([4, 30, 68, 213, 40, 202, 148, 70, 0])

def gr0_colors(colors):
    if len(colors) == 5:
        bg_index = 2
        lm_index = 1
    else:
        bg_index = 6
        lm_index = 5
    bg = colors[bg_index]
    cr = bg & 0xf0;
    lm = colors[lm_index] & 0x0f
    fg = cr | lm
    return fg, bg

# Don't export the utility functions 
__all__ = ['atari_color_to_rgb', 'powerup_colors', 'gr0_colors']


if __name__ == "__main__":
    for i in range(33):
        print i, gtia_ntsc_to_rgb(i), gtia_pal_to_rgb(i)
