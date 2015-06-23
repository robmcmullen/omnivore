##########################################################################
#
# Processor specific code

# CPU = "8080"
# Description = "Intel 8080 8-bit microprocessor."
# DataWidth = 8  # 8-bit data
# AddressWidth = 16  # 16-bit addresses

# Maximum length of an instruction (for formatting purposes)
maxLength = 3

# Leadin bytes for multibyte instructions
leadInBytes = []

# Addressing mode table
# List of addressing modes and corresponding format strings for operands.
addressModeTable = {
"implied"    : "",
"rega"       : "a",
"regb"       : "b",
"regc"       : "c",
"regd"       : "d",
"rege"       : "e",
"regh"       : "h",
"regl"       : "h",
"regm"       : "m",
"regsp"      : "sp",
"regbb"      : "b,b",
"regbc"      : "b,c",
"regbd"      : "b,d",
"regbe"      : "b,e",
"regbh"      : "b,h",
"regbl"      : "b,l",
"regbm"      : "b,m",
"regba"      : "b,a",
"regcb"      : "c,b",
"regcc"      : "c,c",
"regcd"      : "c,d",
"regce"      : "c,e",
"regch"      : "c,h",
"regcl"      : "c,l",
"regcm"      : "c,m",
"regca"      : "c,a",
"regdb"      : "d,b",
"regdc"      : "d,c",
"regdd"      : "d,d",
"regde"      : "d,e",
"regdh"      : "d,h",
"regdl"      : "d,l",
"regdm"      : "d,m",
"regda"      : "d,a",
"regeb"      : "e,b",
"regec"      : "e,c",
"reged"      : "e,d",
"regee"      : "e,e",
"regeh"      : "e,h",
"regel"      : "e,l",
"regem"      : "e,m",
"regea"      : "e,a",
"reghb"      : "h,b",
"reghc"      : "h,c",
"reghd"      : "h,d",
"reghe"      : "h,e",
"reghh"      : "h,h",
"reghl"      : "h,l",
"reghm"      : "h,m",
"regha"      : "h,a",
"reglb"      : "l,b",
"reglc"      : "l,c",
"regld"      : "l,d",
"regle"      : "l,e",
"reglh"      : "l,h",
"regll"      : "l,l",
"reglm"      : "l,m",
"regla"      : "l,a",
"regmb"      : "m,b",
"regmc"      : "m,c",
"regmd"      : "m,d",
"regme"      : "m,e",
"regmh"      : "m,h",
"regml"      : "m,l",
"regma"      : "m,a",
"regab"      : "a,b",
"regac"      : "a,c",
"regad"      : "a,d",
"regae"      : "a,e",
"regah"      : "a,h",
"regal"      : "a,l",
"regam"      : "a,m",
"regaa"      : "a,a",
"immb"       : "b,${0:02X}",
"immc"       : "c,${0:02X}",
"immd"       : "d,${0:02X}",
"immh"       : "h,${0:02X}",
"immm"       : "m,${0:02X}",
"immxb"      : "b,${1:02X}{0:02X}",
"immxd"      : "d,${1:02X}{0:02X}",
"immxh"      : "h,${1:02X}{0:02X}",
"immxsp"     : "sp,${1:02X}{0:02X}",
"direct"     : "${1:02X}{0:02X}",
}

# Op Code Table
# Key is numeric opcode (possibly multiple bytes)
# Value is a list:
#   # bytes
#   mnemonic
#   addressing mode
#   flags (e.g. pcr)
opcodeTable = {

0x00 : [ 1, "nop",  "implied"    ],
0x01 : [ 3, "lxi",  "immxb"      ],
0x02 : [ 1, "stax", "regb"       ],
0x03 : [ 1, "inx",  "regb"       ],
0x04 : [ 1, "inr",  "regb"       ],
0x05 : [ 1, "dcr",  "regb"       ],
0x06 : [ 2, "mvi",  "immb"       ],
0x07 : [ 1, "rlc",  "implied"    ],
0x09 : [ 1, "dad",  "regb"       ],
0x0a : [ 1, "ldax", "regb"       ],
0x0b : [ 1, "dcx",  "regb"       ],
0x0c : [ 1, "inr",  "regc"       ],
0x0d : [ 1, "dcr",  "regc"       ],
0x0e : [ 2, "mvi",  "immc"       ],
0x0f : [ 1, "rrc",  "implied"    ],

0x11 : [ 3, "lxi",  "immxd"      ],
0x12 : [ 1, "stax", "regd"       ],
0x13 : [ 1, "inx",  "regd"       ],
0x14 : [ 1, "inr",  "regd"       ],
0x15 : [ 1, "dcr",  "regd"       ],
0x16 : [ 2, "mvi",  "immd"       ],
0x17 : [ 1, "ral",  "implied"    ],
0x19 : [ 1, "dad",  "implied"    ],
0x1a : [ 1, "ldax", "regd"       ],
0x1b : [ 1, "dcx",  "regd"       ],
0x1c : [ 1, "inr",  "rege"       ],
0x1d : [ 1, "dcr",  "rege"       ],
0x1e : [ 1, "mvi",  "rege"       ],
0x1f : [ 1, "rar",  "implied"    ],

0x21 : [ 3, "lxi",  "immh"      ],
0x22 : [ 1, "shld", "implied"   ],
0x23 : [ 1, "inx",  "regh"      ],
0x24 : [ 1, "inr",  "regh"      ],
0x25 : [ 1, "dcr",  "regh"      ],
0x26 : [ 2, "mvi",  "regh"      ],
0x27 : [ 1, "daa",  "implied"   ],
0x29 : [ 1, "dad",  "regh"      ],
0x2a : [ 3, "lhld", "direct"    ],
0x2b : [ 1, "dcx",  "regh"      ],
0x2c : [ 1, "inr",  "regl"      ],
0x2d : [ 1, "dcr",  "regl"      ],
0x2e : [ 2, "mvi",  "regl"      ],
0x2f : [ 1, "cma",  "implied"   ],

0x31 : [ 3, "lxi",  "immxsp"    ],
0x32 : [ 3, "sta",  "direct"    ],
0x33 : [ 1, "inx",  "regsp"     ],
0x34 : [ 1, "inr",  "regm"      ],
0x35 : [ 1, "dcr",  "regm"      ],
0x36 : [ 2, "mvi",  "immm"      ],
0x37 : [ 1, "stc",  "implied"   ],
0x39 : [ 1, "dad",  "regsp"     ],
0x3a : [ 3, "lda",  "direct"    ],
0x3b : [ 1, "dcx",  "regsp"     ],
0x3c : [ 1, "inr",  "rega"      ],
0x3d : [ 1, "dcr",  "rega"      ],
0x3e : [ 2, "mvi",  "rega"      ],
0x3f : [ 1, "cmc",  "implied"   ],

0x40 : [ 1, "mov",  "regbb"     ],
0x41 : [ 1, "mov",  "regbc"     ],
0x42 : [ 1, "mov",  "regbd"     ],
0x43 : [ 1, "mov",  "regbe"     ],
0x44 : [ 1, "mov",  "regbh"     ],
0x45 : [ 1, "mov",  "regbl"     ],
0x46 : [ 1, "mov",  "regbm"     ],
0x47 : [ 1, "mov",  "regba"     ],
0x48 : [ 1, "mov",  "regcb"     ],
0x49 : [ 1, "mov",  "regcc"     ],
0x4a : [ 1, "mov",  "regcd"     ],
0x4b : [ 1, "mov",  "regce"     ],
0x4c : [ 1, "mov",  "regch"     ],
0x4d : [ 1, "mov",  "regcl"     ],
0x4e : [ 1, "mov",  "regcm"     ],
0x4f : [ 1, "mov",  "regca"     ],

0x50 : [ 1, "mov",  "regdb"     ],
0x51 : [ 1, "mov",  "regdc"     ],
0x52 : [ 1, "mov",  "regdd"     ],
0x53 : [ 1, "mov",  "regde"     ],
0x54 : [ 1, "mov",  "regdh"     ],
0x55 : [ 1, "mov",  "regdl"     ],
0x56 : [ 1, "mov",  "regdm"     ],
0x57 : [ 1, "mov",  "regda"     ],
0x58 : [ 1, "mov",  "regeb"     ],
0x59 : [ 1, "mov",  "regec"     ],
0x5a : [ 1, "mov",  "reged"     ],
0x5b : [ 1, "mov",  "regee"     ],
0x5c : [ 1, "mov",  "regeh"     ],
0x5d : [ 1, "mov",  "regel"     ],
0x5e : [ 1, "mov",  "regem"     ],
0x5f : [ 1, "mov",  "regea"     ],

0x60 : [ 1, "mov",  "reghb"     ],
0x61 : [ 1, "mov",  "reghc"     ],
0x62 : [ 1, "mov",  "reghd"     ],
0x63 : [ 1, "mov",  "reghe"     ],
0x64 : [ 1, "mov",  "reghh"     ],
0x65 : [ 1, "mov",  "reghl"     ],
0x66 : [ 1, "mov",  "reghm"     ],
0x67 : [ 1, "mov",  "regha"     ],
0x68 : [ 1, "mov",  "reglb"     ],
0x69 : [ 1, "mov",  "reglc"     ],
0x6a : [ 1, "mov",  "regld"     ],
0x6b : [ 1, "mov",  "regle"     ],
0x6c : [ 1, "mov",  "reglh"     ],
0x6d : [ 1, "mov",  "regll"     ],
0x6e : [ 1, "mov",  "reglm"     ],
0x6f : [ 1, "mov",  "regla"     ],

0x70 : [ 1, "mov",  "regmb"     ],
0x71 : [ 1, "mov",  "regmc"     ],
0x72 : [ 1, "mov",  "regmd"     ],
0x73 : [ 1, "mov",  "regme"     ],
0x74 : [ 1, "mov",  "regmh"     ],
0x75 : [ 1, "mov",  "regml"     ],
0x76 : [ 1, "hlt",  "implied"   ],
0x77 : [ 1, "mov",  "regma"     ],
0x78 : [ 1, "mov",  "regab"     ],
0x79 : [ 1, "mov",  "regac"     ],
0x7a : [ 1, "mov",  "regad"     ],
0x7b : [ 1, "mov",  "regae"     ],
0x7c : [ 1, "mov",  "regah"     ],
0x7d : [ 1, "mov",  "regal"     ],
0x7e : [ 1, "mov",  "regam"     ],
0x7f : [ 1, "mov",  "regaa"     ],

}

# End of processor specific code
##########################################################################

 
#     ["add     b",   1],  # 80
#     ["add     c",   1],  # 81
#     ["add     d",   1],  # 82
#     ["add     e",   1],  # 83
#     ["add     h",   1],  # 84
#     ["add     l",   1],  # 85
#     ["add     m",   1],  # 86
#     ["add     a",   1],  # 87
#     ["adc     b",   1],  # 88
#     ["adc     c",   1],  # 89
#     ["adc     d",   1],  # 8A
#     ["adc     e",   1],  # 8B
#     ["adc     h",   1],  # 8C
#     ["adc     l",   1],  # 8D
#     ["adc     m",   1],  # 8E
#     ["adc     a",   1],  # 8F
# 
#     ["sub     b",   1],  # 90
#     ["sub     c",   1],  # 91
#     ["sub     d",   1],  # 92
#     ["sub     e",   1],  # 93
#     ["sub     h",   1],  # 94
#     ["sub     l",   1],  # 95
#     ["sub     m",   1],  # 96
#     ["sub     a",   1],  # 97
#     ["sbb     b",   1],  # 98
#     ["sbb     c",   1],  # 99
#     ["sbb     d",   1],  # 9A
#     ["sbb     e",   1],  # 9B
#     ["sbb     h",   1],  # 9C
#     ["sbb     l",   1],  # 9D
#     ["sbb     m",   1],  # 9E
#     ["sbb     a",   1],  # 9F
# 
#     ["ana     b",   1],  # A0
#     ["ana     c",   1],  # A1
#     ["ana     d",   1],  # A2
#     ["ana     e",   1],  # A3
#     ["ana     h",   1],  # A4
#     ["ana     l",   1],  # A5
#     ["ana     m",   1],  # A6
#     ["ana     a",   1],  # A7
#     ["xra     b",   1],  # A8
#     ["xra     c",   1],  # A9
#     ["xra     d",   1],  # AA
#     ["xra     e",   1],  # AB
#     ["xra     h",   1],  # AC
#     ["xra     l",   1],  # AD
#     ["xra     m",   1],  # AE
#     ["xra     a",   1],  # AF
# 
#     ["ora     b",   1],  # B0
#     ["ora     c",   1],  # B1
#     ["ora     d",   1],  # B2
#     ["ora     e",   1],  # B3
#     ["ora     h",   1],  # B4
#     ["ora     l",   1],  # B5
#     ["ora     m",   1],  # B6
#     ["ora     a",   1],  # B7
#     ["cmp     b",   1],  # B8
#     ["cmp     c",   1],  # B9
#     ["cmp     d",   1],  # BA
#     ["cmp     e",   1],  # BB
#     ["cmp     h",   1],  # BC
#     ["cmp     l",   1],  # BD
#     ["cmp     m",   1],  # BE
#     ["cmp     a",   1],  # BF
# 
#     ["rnz",         1],  # C0
#     ["pop     b",   1],  # C1
#     ["jnz     ",    3],  # C2
#     ["jmp     ",    3],  # C3
#     ["cnz     ",    3],  # C4
#     ["push    b",   1],  # C5
#     ["adi     ",    2],  # C6
#     ["rst     0",   1],  # C7
#     ["rz",          1],  # C8
#     ["ret",         1],  # C9
#     ["jz      ",    3],  # CA
#     ["cz      ",    3],  # CC
#     ["call    ",    3],  # CD
#     ["aci     ",    2],  # CE
#     ["rst     1",   1],  # CF
# 
#     ["rnc",         1],  # D0
#     ["pop     d",   1],  # D1
#     ["jnc     ",    3],  # D2
#     ["out     ",    2],  # D3
#     ["cnc     ",    3],  # D4
#     ["push    d",   1],  # D5
#     ["sui     ",    2],  # D6
#     ["rst     2",   1],  # D7
#     ["rc",          1],  # D8
#     ["jc      ",    3],  # DA
#     ["in      ",    2],  # DB
#     ["cc      ",    3],  # DC
#     ["sbi     ",    2],  # DE
#     ["rst     3",   1],  # DF
# 
#     ["rpo",         1],  # E0
#     ["pop     h",   1],  # E1
#     ["jpo     ",    3],  # E2
#     ["xthl",        1],  # E3
#     ["cpo     ",    3],  # E4
#     ["push    h",   1],  # E5
#     ["ani     ",    2],  # E6
#     ["rst     4",   1],  # E7
#     ["rpe",         1],  # E8
#     ["pchl",        1],  # E9
#     ["jpe     ",    3],  # EA
#     ["xchg",        1],  # EB
#     ["cpe     ",    3],  # EC
#     ["xri     ",    2],  # EE
#     ["rst     5",   1],  # EF
# 
#     ["rp",          1],  # F0
#     ["pop     psw", 1],  # F1
#     ["jp      ",    3],  # F2
#     ["di",          1],  # F3
#     ["cp      ",    3],  # F4
#     ["push    psw", 1],  # F5
#     ["ori     ",    2],  # F6
#     ["rst     6",   1],  # F7
#     ["rm",          1],  # F8
#     ["sphl",        1],  # F9
#     ["jm      ",    3],  # FA
#     ["ei",          1],  # FB
#     ["cm      ",    3],  # FC
#     ["cpi     ",    2],  # FE
#     ["rst     7",   1],  # FF
