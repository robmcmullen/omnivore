# color blending utilities

import math

import numpy as np


def get_blended_color_registers(colors, blend_color):
    registers = []
    base_blend = [(r * 7)/8 for r in blend_color]
    for c in colors:
        r = [c[i]/8 + base_blend[i] for i in range(3)]
        registers.append(r)
    return registers


def get_dimmed_color_registers(colors, background_color, dimmed_color):
    registers = []
    dimmed_difference = [b - d for b, d in zip(background_color, dimmed_color)]
    for c in colors:
        r = [max(0, c[i]- dimmed_difference[i]) for i in range(3)]
        registers.append(r)
    return registers


def calc_blended_rgb(rgb_colors, blend_color):
    registers = np.zeros((256, 3), dtype=np.uint8)
    base_blend = [(r * 7) for r in blend_color]
    for i in range(len(registers)):
        registers[i] = [(int(rgb_colors[i,j]) + base_blend[j]) // 8 for j in range(3)]
    return registers


def calc_dimmed_rgb(rgb_colors, background_color, dimmed_color):
    registers = np.zeros((256, 3), dtype=np.uint8)
    dimmed_difference = [b - d for b, d in zip(background_color, dimmed_color)]
    for i in range(len(registers)):
        registers[i] = [max(0, int(rgb_colors[i,j]) - dimmed_difference[j]) for j in range(3)]
    return registers
