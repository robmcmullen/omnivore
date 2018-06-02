#!/usr/bin/env python
#
# Note: can't figure out a way to determine the offset of structure members
# after construction, so I've inserted additional entries into the structure
# that contain the raw offset into the file.
#
# I generated these using the regex search/replace (note the replace is multi-
# line):
#
# find: \"(\w+)\" */ *(.+)
# replace: "\1_offset" / Tell,
#          "\1\" / \2

import numpy as np

from construct import *

import logging
log = logging.getLogger(__name__)


Atari800_MACHINE_XLXE = 1
MEMORY_RAM_320_RAMBO = 320
MEMORY_RAM_320_COMPY_SHOP = 321
BB_RAM_SIZE = 0x10000
COMMAND_FRAME_SIZE = 6
DATA_BUFFER_SIZE = 256 + 3

def init_atari800_struct():
    Fname = Struct(
        "len_offset" / Tell,
        "len" / Int16ul,
        "name_offset" / Tell,
        "name" / String(this.len),
        )

    Sio = Struct(
        "status_offset" / Tell,
        "status" / Int32sl,
        "filename_offset" / Tell,
        "filename" / Fname,
        )

    a8save = "a8save" / Struct(
        "signature_segment" / Tell,
        "signature_offset" / Tell,
        "signature" / Struct(
            "magic_offset" / Tell,
            "magic" / Const(b"ATARI800"),
            "version_offset" / Tell,
            "version" / Int8ul,
            "verbose_offset" / Tell,
            "verbose" / Int8ul,
            "signature_offset_end" / Tell,
            ),
        "signature_segment_end" / Tell,

        "machine_type_segment" / Tell,
        "machine_type_offset" / Tell,
        "machine_type" / Struct(
            "tv_mode_offset" / Tell,
            "tv_mode" / Int8ul,
            "id_offset" / Tell,
            "id" / Int8ul,
            "machine_type_offset_end" / Tell,
            ),
        "machine_type_segment_end" / Tell,

        "xl_xe_segment" / Tell,
        "xl_xe_offset" / Tell,
        "xl_xe" / If(this.machine_type.id > 0,
            Struct(
                "builtin_basic_offset" / Tell,
                "builtin_basic" / Int8ul,
                "keyboard_leds_offset" / Tell,
                "keyboard_leds" / Int8ul,
                "f_keys_offset" / Tell,
                "f_keys" / Int8ul,
                "jumper_offset" / Tell,
                "jumper" / Int8ul,
                "builtin_game_offset" / Tell,
                "builtin_game" / Int8ul,
                "keyboard_detached_offset" / Tell,
                "keyboard_detached" / Int8ul,
                "xl_xe_offset_end" / Tell,
                )
            ),
        "xl_xe_segment_end" / Tell,

        # CARTRIDGE
        "cartridge_segment" / Tell,
        "cartridge_offset" / Tell,
        "cartridge" / Struct(
            "cartridge_flag_offset" / Tell,
            "cartridge_flag" / Int32sl,
            "left_cart_filename_offset" / Tell,
            "left_cart_filename" / If(this.cartridge_flag != 0, Fname),
            "left_cart_state_offset" / Tell,
            "left_cart_state" / If(this.cartridge_flag != 0, Int32sl),
            "right_cart_type_offset" / Tell,
            "right_cart_type" / If(this.cartridge_flag < 0, Int32sl),
            "right_cart_filename_offset" / Tell,
            "right_cart_filename" /  If(this.cartridge_flag < 0, Fname),
            "right_cart_state_offset" / Tell,
            "right_cart_state" / If(this.cartridge_flag < 0, Int32sl),
            "cartridge_offset_end" / Tell,
            ),
        "cartridge_segment_end" / Tell,

        # SIO
        # StateSav_SaveINT((int *) &SIO_drive_status[i], 1);
        # StateSav_SaveFNAME(SIO_filename[i]);
        "SIO_1_offset" / Tell,
        "SIO_1" / Sio,
        "SIO_2_offset" / Tell,
        "SIO_2" / Sio,
        "SIO_3_offset" / Tell,
        "SIO_3" / Sio,
        "SIO_4_offset" / Tell,
        "SIO_4" / Sio,
        "SIO_5_offset" / Tell,
        "SIO_5" / Sio,
        "SIO_6_offset" / Tell,
        "SIO_6" / Sio,
        "SIO_7_offset" / Tell,
        "SIO_7" / Sio,
        "SIO_8_offset" / Tell,
        "SIO_8" / Sio,

        # ANTIC
        "ANTIC_segment" / Tell,
        "ANTIC_offset" / Tell,
        "ANTIC" / Struct(
            "DMACTL_offset" / Tell,
            "DMACTL" / Int8ul,
            "CHACTL_offset" / Tell,
            "CHACTL" / Int8ul,
            "HSCROL_offset" / Tell,
            "HSCROL" / Int8ul,
            "VSCROL_offset" / Tell,
            "VSCROL" / Int8ul,
            "PMBASE_offset" / Tell,
            "PMBASE" / Int8ul,
            "CHBASE_offset" / Tell,
            "CHBASE" / Int8ul,
            "NMIEN_offset" / Tell,
            "NMIEN" / Int8ul,
            "NMIST_offset" / Tell,
            "NMIST" / Int8ul,
            "_ir_offset" / Tell,
            "_ir" / Int8ul,
            "_anticmode_offset" / Tell,
            "_anticmode" / Int8ul,
            "_dctr_offset" / Tell,
            "_dctr" / Int8ul,
            "_lastline_offset" / Tell,
            "_lastline" / Int8ul,
            "_need_dl_offset" / Tell,
            "_need_dl" / Int8ul,
            "_vscrol_off_offset" / Tell,
            "_vscrol_off" / Int8ul,

            "DLIST_offset" / Tell,
            "DLIST" / Int16ul,
            "_screenaddr_offset" / Tell,
            "_screenaddr" / Int16ul,

            "xpos_offset" / Tell,
            "xpos" / Int32sl,
            "_xpos_limit_offset" / Tell,
            "_xpos_limit" / Int32sl,
            "ypos_offset" / Tell,
            "ypos" / Int32sl,
            "ANTIC_offset_end" / Tell,
            ),
        "ANTIC_segment_end" / Tell,

        #CPU
        "CPU_segment" / Tell,
        "CPU_offset" / Tell,
        "CPU" / Struct(
            "A_offset" / Tell,
            "A" / Int8ul,
            "P_offset" / Tell,
            "P" / Int8ul,
            "S_offset" / Tell,
            "S" / Int8ul,
            "X_offset" / Tell,
            "X" / Int8ul,
            "Y_offset" / Tell,
            "Y" / Int8ul,
            "IRQ_offset" / Tell,
            "IRQ" / Int8ul,
            "CPU_offset_end" / Tell,
            ),
        "CPU_segment_end" / Tell,

        #Memory
        "AXLON_segment" / Tell,
        "AXLON_offset" / Tell,
        "AXLON" / If(this.machine_type.id == 0,
            Struct(
                "num_banks_offset" / Tell,
                "num_banks" / Int8ul,
                "curbank_offset" / Tell,
                "curbank" / If (this.num_banks > 0, Int32sl),
                "0f_mirror_offset" / Tell,
                "0f_mirror" / If (this.num_banks > 0, Int32sl),
                "axlon_ram_offset" / Tell,
                "axlon_ram" / If (this.num_banks > 0, Bytes(this.num_banks * 0x4000)),
            "AXLON_offset_end" / Tell,
                )
            ),
        "AXLON_segment_end" / Tell,

        "MOSAIC_segment" / Tell,
        "MOSAIC_offset" / Tell,
        "MOSAIC" / If(this.machine_type.id == 0,
            Struct(
                "num_banks_offset" / Tell,
                "num_banks" / Int8ul,
                "curbank_offset" / Tell,
                "curbank" / If (this.num_banks > 0, Int32sl),
                "mosaic_ram_offset" / Tell,
                "mosaic_ram" / If (this.num_banks > 0, Bytes(this.num_banks * 0x1000)),
            "MOSAIC_offset_end" / Tell,
                )
            ),
        "MOSAIC_segment_end" / Tell,

        "RAM_segment" / Tell,
        "RAM_offset" / Tell,
        "ram" / Struct(
            "base_ram_size_kb_offset" / Tell,
            "base_ram_size_kb" / Int32sl,
            "ram_segment" / Tell,
            "ram_offset" / Tell,
            "ram" / Bytes(65536),
            "ram_segment_end" / Tell,
            "ram_attrib_segment" / Tell,
            "attrib_offset" / Tell,
            "attrib" / Bytes(65536),
            "ram_attrib_segment_end" / Tell,
            "RAM_offset_end" / Tell,
            ),
        "RAM_segment_end" / Tell,

        "XLRAM_segment" / Tell,
        "XLRAM_offset" / Tell,
        "XLRAM" / If(this.machine_type.id == Atari800_MACHINE_XLXE,
            Struct(
                "basic_$A000_segment" / Tell,
                "basic_offset" / Tell,
                "basic" / If(this._.signature.verbose != 0, Bytes(8192)),
                "basic_$A000_segment_end" / Tell,
                "under_cartA0BF_$A000_segment" / Tell,
                "under_cartA0BF_offset" / Tell,
                "under_cartA0BF" / Bytes(8192),
                "under_cartA0BF_$A000_segment_end" / Tell,
                "os_offset_$C000_segment" / Tell,
                "os_offset" / Tell,
                "os" / If(this._.signature.verbose != 0, Bytes(16384)),
                "os_offset_$C000_segment_end" / Tell,
                "under_atarixl_os_offset_$C000_segment" / Tell,
                "under_atarixl_os_offset" / Tell,
                "under_atarixl_os" / Bytes(16384),
                "under_atarixl_os_offset_$C000_segment" / Tell,
                "xegame_offset_$E000_segment_end" / Tell,
                "xegame_offset" / Tell,
                "xegame" / If(this._.signature.verbose != 0, Bytes(0x2000)),
                "xegame_offset_$E000_segment_end" / Tell,
            "XLRAM_offset_end" / Tell,
                )
            ),
        "XLRAM_segment_end" / Tell,

        "num_16k_xe_banks_offset" / Tell,
        "num_16k_xe_banks" / Int32sl,

        "ram_size_kb_before_rambo_offset" / Tell,
        "ram_size_kb_before_rambo" / Computed(this.ram.base_ram_size_kb + (this.num_16k_xe_banks * 16)),

        # rambo_kb will be populated if RAMBO = 320 (0x140), COMPY_SHOP = 321 (0x141)
        "rambo_kb_offset" / Tell,
        "rambo_kb" / IfThenElse(this.ram_size_kb_before_rambo & 0xfffe == 0x140, Int32sl, Computed(0)), # value is MEMORY_ram_size - 320

        "ram_size_offset" / Tell,
        "ram_size" / Computed(this.ram_size_kb_before_rambo + this.rambo_kb),

        "PORTB_offset" / Tell,
        "PORTB" / Int8ul,

        "CartA0BF_enabled_offset" / Tell,
        "CartA0BF_enabled" / Int32sl,

        "atarixe_memory_offset" / Tell,
        "atarixe_memory" / If(this.ram_size > 64,
            Struct(
                "size_offset" / Tell,
                "size" / Computed((1 + (this.ram_size - 64) / 16) * 16384),
                "xeram_offset" / Tell,
                "xeram" / Bytes(this.size),
                "selftest_enabled_offset" / Tell,
                "selftest_enabled" / Computed(lambda ctx: (ctx._.PORTB & 0x81) == 0x01 and not ((ctx._.PORTB & 0x30) != 0x30 and ctx._.ram_size == MEMORY_RAM_320_COMPY_SHOP) and not ((ctx._.PORTB & 0x10) == 0 and ctx._.ram_size == 1088)),
                "antic_bank_under_selftest_offset" / Tell,
                "antic_bank_under_selftest" / If(this.selftest_enabled, Bytes(0x800)),
            "atarixe_memory_offset_end" / Tell,
                )
            ),

        "mapram_segment" / Tell,
        "mapram_offset" / Tell,
        "mapram" / If(lambda ctx: ctx.machine_type.id == Atari800_MACHINE_XLXE and ctx.ram_size > 20,
            Struct(
                "enable_offset" / Tell,
                "enable" / Int32sl,
                "memory_offset" / Tell,
                "memory" / If(this.enable != 0, Bytes(0x800)),
                "mapram_offset_end" / Tell,
                )
            ),
        "mapram_segment_end" / Tell,

        "PC_segment" / Tell,
        "PC_offset" / Tell,
        "PC" / Int16ul,
        "PC_offset_end" / Tell,
        "PC_segment_end" / Tell,

        "GTIA_segment" / Tell,
        "GTIA_offset" / Tell,
        "GTIA" / Struct(
            "HPOSP0_offset" / Tell,
            "HPOSP0" / Int8ul,
            "HPOSP1_offset" / Tell,
            "HPOSP1" / Int8ul,
            "HPOSP2_offset" / Tell,
            "HPOSP2" / Int8ul,
            "HPOSP3_offset" / Tell,
            "HPOSP3" / Int8ul,
            "HPOSM0_offset" / Tell,
            "HPOSM0" / Int8ul,
            "HPOSM1_offset" / Tell,
            "HPOSM1" / Int8ul,
            "HPOSM2_offset" / Tell,
            "HPOSM2" / Int8ul,
            "HPOSM3_offset" / Tell,
            "HPOSM3" / Int8ul,
            "PF0PM_offset" / Tell,
            "PF0PM" / Int8ul,
            "PF1PM_offset" / Tell,
            "PF1PM" / Int8ul,
            "PF2PM_offset" / Tell,
            "PF2PM" / Int8ul,
            "PF3PM_offset" / Tell,
            "PF3PM" / Int8ul,
            "M0PL_offset" / Tell,
            "M0PL" / Int8ul,
            "M1PL_offset" / Tell,
            "M1PL" / Int8ul,
            "M2PL_offset" / Tell,
            "M2PL" / Int8ul,
            "M3PL_offset" / Tell,
            "M3PL" / Int8ul,
            "P0PL_offset" / Tell,
            "P0PL" / Int8ul,
            "P1PL_offset" / Tell,
            "P1PL" / Int8ul,
            "P2PL_offset" / Tell,
            "P2PL" / Int8ul,
            "P3PL_offset" / Tell,
            "P3PL" / Int8ul,
            "SIZEP0_offset" / Tell,
            "SIZEP0" / Int8ul,
            "SIZEP1_offset" / Tell,
            "SIZEP1" / Int8ul,
            "SIZEP2_offset" / Tell,
            "SIZEP2" / Int8ul,
            "SIZEP3_offset" / Tell,
            "SIZEP3" / Int8ul,
            "SIZEM_offset" / Tell,
            "SIZEM" / Int8ul,
            "GRAFP0_offset" / Tell,
            "GRAFP0" / Int8ul,
            "GRAFP1_offset" / Tell,
            "GRAFP1" / Int8ul,
            "GRAFP2_offset" / Tell,
            "GRAFP2" / Int8ul,
            "GRAFP3_offset" / Tell,
            "GRAFP3" / Int8ul,
            "GRAFM_offset" / Tell,
            "GRAFM" / Int8ul,
            "COLPM0_offset" / Tell,
            "COLPM0" / Int8ul,
            "COLPM1_offset" / Tell,
            "COLPM1" / Int8ul,
            "COLPM2_offset" / Tell,
            "COLPM2" / Int8ul,
            "COLPM3_offset" / Tell,
            "COLPM3" / Int8ul,
            "COLPF0_offset" / Tell,
            "COLPF0" / Int8ul,
            "COLPF1_offset" / Tell,
            "COLPF1" / Int8ul,
            "COLPF2_offset" / Tell,
            "COLPF2" / Int8ul,
            "COLPF3_offset" / Tell,
            "COLPF3" / Int8ul,
            "COLBK_offset" / Tell,
            "COLBK" / Int8ul,
            "PRIOR_offset" / Tell,
            "PRIOR" / Int8ul,
            "VDELAY_offset" / Tell,
            "VDELAY" / Int8ul,
            "GRACTL_offset" / Tell,
            "GRACTL" / Int8ul,

            "_consol_mask_offset" / Tell,
            "_consol_mask" / Int8ul,
            "_speaker_offset" / Tell,
            "_speaker" / Int32sl,
            "_next_console_value_offset" / Tell,
            "_next_console_value" / Int32sl,
            "_TRIG_latch_offset" / Tell,
            "_TRIG_latch" / Bytes(4),
            "_GTIA_offset_end" / Tell,
            ),
        "GTIA_segment_end" / Tell,

        "PIA_segment" / Tell,
        "PIA_offset" / Tell,
        "PIA" / Struct(
            "PACTL_offset" / Tell,
            "PACTL" / Int8ul,
            "PBCTL_offset" / Tell,
            "PBCTL" / Int8ul,
            "PORTA_offset" / Tell,
            "PORTA" / Int8ul,
            "PORTB_offset" / Tell,
            "PORTB" / Int8ul,

            "_PORTA_mask_offset" / Tell,
            "_PORTA_mask" / Int8ul,
            "_PORTB_mask_offset" / Tell,
            "_PORTB_mask" / Int8ul,

            "_CA2_offset" / Tell,
            "_CA2" / Int32sl,
            "_CA2_negpending_offset" / Tell,
            "_CA2_negpending" / Int32sl,
            "_CA2_pospending_offset" / Tell,
            "_CA2_pospending" / Int32sl,
            "_CB2_offset" / Tell,
            "_CB2" / Int32sl,
            "_CB2_negpending_offset" / Tell,
            "_CB2_negpending" / Int32sl,
            "_CB2_pospending_offset" / Tell,
            "_CB2_pospending" / Int32sl,
            "_PIA_offset_end" / Tell,
            ),
        "PIA_segment_end" / Tell,

        "POKEY_segment" / Tell,
        "POKEY_offset" / Tell,
        "POKEY" / Struct(
            "KBCODE_offset" / Tell,
            "KBCODE" / Int8ul,
            "IRQST_offset" / Tell,
            "IRQST" / Int8ul,
            "IRQEN_offset" / Tell,
            "IRQEN" / Int8ul,
            "SKCTL_offset" / Tell,
            "SKCTL" / Int8ul,

            "_shift_key_offset" / Tell,
            "_shift_key" / Int32sl,
            "_keypressed_offset" / Tell,
            "_keypressed" / Int32sl,
            "_DELAYED_SERIN_IRQ_offset" / Tell,
            "_DELAYED_SERIN_IRQ" / Int32sl,
            "_DELAYED_SEROUT_IRQ_offset" / Tell,
            "_DELAYED_SEROUT_IRQ" / Int32sl,
            "_DELAYED_XMTDONE_IRQ_offset" / Tell,
            "_DELAYED_XMTDONE_IRQ" / Int32sl,

            "AUDF1_offset" / Tell,
            "AUDF1" / Int8ul,
            "AUDF2_offset" / Tell,
            "AUDF2" / Int8ul,
            "AUDF3_offset" / Tell,
            "AUDF3" / Int8ul,
            "AUDF4_offset" / Tell,
            "AUDF4" / Int8ul,
            "AUDC1_offset" / Tell,
            "AUDC1" / Int8ul,
            "AUDC2_offset" / Tell,
            "AUDC2" / Int8ul,
            "AUDC3_offset" / Tell,
            "AUDC3" / Int8ul,
            "AUDC4_offset" / Tell,
            "AUDC4" / Int8ul,
            "AUDCTL_offset" / Tell,
            "AUDCTL" / Int8ul,

            "_DivNIRQ_offset" / Tell,
            "_DivNIRQ" / Bytes(16),
            "_DivNMax_offset" / Tell,
            "_DivNMax" / Bytes(16),
            "_Base_mult_offset" / Tell,
            "_Base_mult" / Int32sl,

            "POKEY_offset_end" / Tell,
            ),
        "POKEY_segment_end" / Tell,

        "Extensions_segment" / Tell,
        "XEP80_enabled_offset" / Tell,
        "XEP80_enabled" / Int8ul,
        "XEP80_offset" / Tell,
        "XEP80" / If(this.XEP80_enabled,
            Struct(
                "tbd_offset" / Tell,
                "tbd" / Bytes(8330),
                # 25 INT,1 => 100 bytes
                # 1 WORD,10 => 10 bytes
                # 3 BYTE, 1 => 3 bytes
                # 1 BYTE, 25 => 25 bytes
                # 8192 video ram
                # ---------
                # 8330 bytes
                #
                # INT(&XEP80_port, 1);
                # INT(&show_XEP80, 1);
                # INT(&num_ticks, 1);
                # INT(&output_word, 1);
                # INT(&input_count, 1);
                # INT(&receiving, 1);
                # UWORD(input_queue, 10);
                # INT(&receiving, 1);
                # UBYTE(&last_char, 1);
                # INT(&xpos, 1);
                # INT(&xscroll, 1);
                # INT(&ypos, 1);
                # INT(&cursor_x, 1);
                # INT(&cursor_y, 1);
                # INT(&curs, 1);
                # INT(&old_xpos, 1);
                # INT(&old_ypos, 1);
                # INT(&lmargin, 1);
                # INT(&rmargin, 1);
                # UBYTE(&attrib_a, 1);
                # UBYTE(&attrib_b, 1);
                # INT(&list_mode, 1);
                # INT(&escape_mode, 1);
                # INT(&char_set, 1);
                # INT(&cursor_on, 1);
                # INT(&cursor_blink, 1);
                # INT(&cursor_overwrite, 1);
                # INT(&blink_reverse, 1);
                # INT(&inverse_mode, 1);
                # INT(&screen_output, 1);
                # INT(&burst_mode, 1);
                # INT(&graphics_mode, 1);
                # INT(&pal_mode, 1);
                # UBYTE(&ptr, 25);
                # UBYTE(video_ram, 8192);
            "XEP80_offset_end" / Tell,
                )
            ),

        "PBI_offset" / Tell,
        "PBI" / Struct(
            "D1FF_LATCH_offset" / Tell,
            "D1FF_LATCH" / Int8ul,
            "D6D7ram_offset" / Tell,
            "D6D7ram" / Int32sl,
            "IRQ_offset" / Tell,
            "IRQ" / Int32sl,
            "PBI_offset_end" / Tell,
            ),

        "PBI_MIO_enabled_offset" / Tell,
        "PBI_MIO_enabled" / Int8ul,
        "PBI_MIO_offset" / Tell,
        "PBI_MIO" / If(this.PBI_MIO_enabled,
            Struct(
                "scsi_disk_filename_offset" / Tell,
                "scsi_disk_filename" / Fname,
                "rom_filename_offset" / Tell,
                "rom_filename" / Fname,
                "ram_size_offset" / Tell,
                "ram_size" / Int32sl,
                "ram_bank_offset_offset" / Tell,
                "ram_bank_offset" / Int32sl,
                "ram_offset" / Tell,
                "ram" / Bytes(this.ram_size),
                "rom_bank_offset" / Tell,
                "rom_bank" / Int8ul,
                "ram_enabled_offset" / Tell,
                "ram_enabled" / Int32sl,
            "PBI_MIO_offset_end" / Tell,
                )
            ),

        "PBI_BB_enabled_offset" / Tell,
        "PBI_BB_enabled" / Int8ul,
        "PBI_BB_offset" / Tell,
        "PBI_BB" / If(this.PBI_BB_enabled,
            Struct(
                "scsi_disk_filename_offset" / Tell,
                "scsi_disk_filename" / Fname,
                "rom_filename_offset" / Tell,
                "rom_filename" / Fname,
                "ram_bank_offset_offset" / Tell,
                "ram_bank_offset" / Int32sl,
                "ram_offset" / Tell,
                "ram" / Bytes(BB_RAM_SIZE),
                "rom_bank_offset" / Tell,
                "rom_bank" / Int8ul,
                "rom_high_bit_offset" / Tell,
                "rom_high_bit" / Int32sl,
                "pcr_offset" / Tell,
                "pcr" / Int8ul,
            "PBI_BB_offset_end" / Tell,
                )
            ),

        "PBI_XLD_enabled_offset" / Tell,
        "PBI_XLD_enabled" / Int8ul,
        "PBI_XLD_offset" / Tell,
        "PBI_XLD" / If(this.PBI_XLD_enabled,
            Struct(
                "xld_v_enabled_offset" / Tell,
                "xld_v_enabled" / Int32sl,
                "xld_d_enabled_offset" / Tell,
                "xld_d_enabled" / Int32sl,
                "xld_d_romfilename_offset" / Tell,
                "xld_d_romfilename" / Fname,
                "xld_v_romfilename_offset" / Tell,
                "xld_v_romfilename" / Fname,
                "votrax_latch_offset" / Tell,
                "votrax_latch" / Int8ul,
                "modem_latch_offset" / Tell,
                "modem_latch" / Int8ul,
                "CommandFrame_offset" / Tell,
                "CommandFrame" / Bytes(COMMAND_FRAME_SIZE),
                "CommandIndex_offset" / Tell,
                "CommandIndex" / Int32sl,
                "DataBuffer_offset" / Tell,
                "DataBuffer" / Bytes(DATA_BUFFER_SIZE),
                "DataIndex_offset" / Tell,
                "DataIndex" / Int32sl,
                "TransferStatus_offset" / Tell,
                "TransferStatus" / Int32sl,
                "ExpectedBytes_offset" / Tell,
                "ExpectedBytes" / Int32sl,
                "VOTRAXSND_busy_offset" / Tell,
                "VOTRAXSND_busy" / Int32sl,
            "PBI_XLD_offset_end" / Tell,
                )
            ),
        "Extensions_segment_end" / Tell,

        )

    return a8save

def get_offsets(container, prefix, comments, segments, dtypes, data_offset=0, current_dtype=None):
    start = 0
    name = "data"
    origin = 0
    for k,v in list(container.items()):
        if k.endswith("_offset"):
            log.debug(("offset", prefix + k[:-7], v))
            comments[v + data_offset] = prefix + k[:-7]
            if current_dtype is not None:
                if len(current_dtype) > 0:
                    dname, dstart, _ = current_dtype.pop()
                    current_dtype.append((dname, dstart, v + data_offset))
                current_dtype.append((k[:-7], v + data_offset, -1))
        elif k.endswith("_offset_end"):
            c = current_dtype
            if c is not None and len(c) > 0:
                dname, dstart, end = c.pop()
                log.debug(("HTOESURCHOSECRUHOEUH", k, dname, dstart, end))
                c.append((dname, dstart, v))
        elif k.endswith("_segment"):
            args = k.split("_")
            args.pop()
            if args[-1].startswith("$"):
                origin = int(args.pop()[1:], 16)
            else:
                origin = 0
            log.debug(("segment:" + prefix + k[:-7], v))
            start = v
            name = " ".join(args)
            current_dtype = []
        elif k.endswith("_segment_end"):
            segments.append((start + data_offset, v + data_offset, origin, name))
            log.debug(("end segment:" + prefix + name, v, segments[-1]))
            if name in dtypes:
                last_dtype = dtypes[name]
                if len(last_dtype) > 0:
                    dname, dstart, _ = last_dtype.pop()
                    last_dtype.append((dname, dstart, v + data_offset))

        elif type(v) == Container:
            log.debug(("Container: %s" % k))
            c = []
            index = get_offsets(v, prefix + "%s_" % k, comments, segments, dtypes, data_offset, c)
            dtypes[k] = c
            log.debug(("End Container: %s" % k, c))


def parse_state(data, data_offset):
    a8save = init_atari800_struct()
    test = a8save.parse(data)
    offsets = {}
    segments = []
    dtypes_setup = {}
    get_offsets(test, "", offsets, segments, dtypes_setup, data_offset)
    dtypes = {}
    for name, index_data in dtypes_setup.items():
        d = []
        log.debug(("dtypes for %s" % name))
        for varname, start, stop in index_data:
            log.debug(("varname", varname, start, stop))
            size = stop - start
            if size == 1:
                d.append((varname, np.uint8))
            elif size == 2:
                d.append((varname, '>u2'))
            elif size == 4:
                d.append((varname, '>i4'))
            else:
                size = stop - start
                if size < 0:
                    size = 1
                d.append((varname, np.uint8, size))
        log.debug(("dtype=%s" % str(d)))
        dtypes[name] = np.dtype(d)
    names = {v: k for k, v in offsets.items()}
    segment_starts = {name: start for start, _, _, name in segments}
    return offsets, names, segments, segment_starts, dtypes


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "rb") as fh:
        data = fh.read()
        offsets, names, segments, segment_starts, dtypes = parse_state(data, 0)
        # print sorted(list(offsets.items()))
        # print "\n".join(["%s: %s" % kv for kv in sorted(list(names.items()))])
        print(dtypes['ANTIC'])
        print(segment_starts['ANTIC'])