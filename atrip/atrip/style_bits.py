import numpy as np

import logging
log = logging.getLogger(__name__)


user_bit_mask = 0x07
not_user_bit_mask = 0xff ^ user_bit_mask
data_bit_mask = 0x08
diff_bit_mask = 0x10
match_bit_mask = 0x20
comment_bit_mask = 0x40
selected_bit_mask = 0x80


def get_style_bits(match=False, comment=False, selected=False, data=False, diff=False, user=0):
    """ Return an int value that contains the specified style bits set.

    Available styles for each byte are:

    match: part of the currently matched search
    comment: user commented area
    selected: selected region
    data: labeled in the disassembler as a data region (i.e. not disassembled)
    """
    style_bits = 0
    if user:
        style_bits |= (user & user_bit_mask)
    if diff:
        style_bits |= diff_bit_mask
    if match:
        style_bits |= match_bit_mask
    if comment:
        style_bits |= comment_bit_mask
    if data:
        style_bits |= data_bit_mask
    if selected:
        style_bits |= selected_bit_mask
    return style_bits


def get_style_mask(**kwargs):
    """Get the bit mask that, when anded with data, will turn off the
    selected bits
    """
    bits = get_style_bits(**kwargs)
    if 'user' in kwargs and kwargs['user']:
        bits |= user_bit_mask
    else:
        bits &= (0xff ^ user_bit_mask)
    return 0xff ^ bits
