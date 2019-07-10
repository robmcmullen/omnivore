# SHMEM input template locations
import numpy as np

VIDEO_WIDTH = 336
VIDEO_HEIGHT = 240

VIDEO_SIZE = VIDEO_WIDTH * VIDEO_HEIGHT
AUDIO_SIZE = 2048
MAIN_MEMORY_SIZE = 1<<16
STATESAV_MAX_SIZE = 210000

INPUT_DTYPE = np.dtype([
    ("keychar", np.uint8),
    ("keycode", np.uint8),
    ("special", np.uint8),
    ("shift", np.uint8),
    ("control", np.uint8),
    ("start", np.uint8),
    ("select", np.uint8),
    ("option", np.uint8),
    ("joy0", np.uint8),
    ("trig0", np.uint8),
    ("joy1", np.uint8),
    ("trig1", np.uint8),
    ("joy2", np.uint8),
    ("trig2", np.uint8),
    ("joy3", np.uint8),
    ("trig3", np.uint8),
    ("mousex", np.uint8),
    ("mousey", np.uint8),
    ("mouse_buttons", np.uint8),
    ("mouse_mode", np.uint8),
])

OUTPUT_DTYPE = np.dtype([
    ("video", np.uint8, VIDEO_SIZE),
    ("audio", np.uint8, AUDIO_SIZE),
    ("tag_size", np.uint32),
    ("tag_cpu", np.uint32),
    ("tag_pc", np.uint32),
    ("tag_base_ram", np.uint32),
    ("tag_base_ram_attrib", np.uint32),
    ("tag_antic", np.uint32),
    ("tag_gtia", np.uint32),
    ("tag_pia", np.uint32),
    ("tag_pokey", np.uint32),
    ("tag_filler", np.uint32, 32 - 9),
    ("flag_selftest_enabled", np.uint8),
    ("flag_filler", np.uint8, 127),
    ("state", np.uint8, STATESAV_MAX_SIZE),
])

CPU_DTYPE = np.dtype([
    ("A", np.uint8),
    ("X", np.uint8),
    ("Y", np.uint8),
    ("SP", np.uint8),
    ("P", np.uint8),
    ("PC", '<u2'),
    ])

ANTIC_DTYPE = np.dtype([
    ("DMACTL", np.uint8),
    ("CHACTL", np.uint8),
    ("HSCROL", np.uint8),
    ("VSCROL", np.uint8),
    ("PMBASE", np.uint8),
    ("CHBASE", np.uint8),
    ("NMIEN", np.uint8),
    ("NMIST", np.uint8),
    ("_ir", np.uint8),
    ("_anticmode", np.uint8),
    ("_dctr", np.uint8),
    ("_lastline", np.uint8),
    ("_need_dl", np.uint8),
    ("_vscrol_off", np.uint8),
    ("DLIST", np.uint16),
    ("_screenaddr", np.uint16),
    ("xpos", np.uint32),
    ("_xpos_limit", np.uint32),
    ("ypos", np.uint32),
    ])

GTIA_DTYPE = np.dtype([
    ("HPOSP0", np.uint8),
    ("HPOSP1", np.uint8),
    ("HPOSP2", np.uint8),
    ("HPOSP3", np.uint8),
    ("HPOSM0", np.uint8),
    ("HPOSM1", np.uint8),
    ("HPOSM2", np.uint8),
    ("HPOSM3", np.uint8),
    ("PF0PM", np.uint8),
    ("PF1PM", np.uint8),
    ("PF2PM", np.uint8),
    ("PF3PM", np.uint8),
    ("M0PL", np.uint8),
    ("M1PL", np.uint8),
    ("M2PL", np.uint8),
    ("M3PL", np.uint8),
    ("P0PL", np.uint8),
    ("P1PL", np.uint8),
    ("P2PL", np.uint8),
    ("P3PL", np.uint8),
    ("SIZEP0", np.uint8),
    ("SIZEP1", np.uint8),
    ("SIZEP2", np.uint8),
    ("SIZEP3", np.uint8),
    ("SIZEM", np.uint8),
    ("GRAFP0", np.uint8),
    ("GRAFP1", np.uint8),
    ("GRAFP2", np.uint8),
    ("GRAFP3", np.uint8),
    ("GRAFM", np.uint8),
    ("COLPM0", np.uint8),
    ("COLPM1", np.uint8),
    ("COLPM2", np.uint8),
    ("COLPM3", np.uint8),
    ("COLPF0", np.uint8),
    ("COLPF1", np.uint8),
    ("COLPF2", np.uint8),
    ("COLPF3", np.uint8),
    ("COLBK", np.uint8),
    ("PRIOR", np.uint8),
    ("VDELAY", np.uint8),
    ("GRACTL", np.uint8),
    ])

PIA_DTYPE = np.dtype([
    ("PACTL", np.uint8),
    ("PBCTL", np.uint8),
    ("PORTA", np.uint8),
    ("PORTB", np.uint8),
    ])

POKEY_DTYPE = np.dtype([
    ("KBCODE", np.uint8),
    ("IRQST", np.uint8),
    ("IRQEN", np.uint8),
    ("SKCTL", np.uint8),
    ("_shift_key", np.uint32),
    ("_keypressed", np.uint32),
    ("_DELAYED_SERIN_IRQ", np.uint32),
    ("_DELAYED_SEROUT_IRQ", np.uint32),
    ("_DELAYED_XMTDONE_IRQ", np.uint32),
    ("AUDF1", np.uint8),
    ("AUDF2", np.uint8),
    ("AUDF3", np.uint8),
    ("AUDF4", np.uint8),
    ("AUDC1", np.uint8),
    ("AUDC2", np.uint8),
    ("AUDC3", np.uint8),
    ("AUDC4", np.uint8),
    ("AUDCTL", np.uint8),
    ("_DivNIRQ", np.uint32),
    ("_DivNMax", np.uint32),
    ("_Base_mult", np.uint32),
    ])
