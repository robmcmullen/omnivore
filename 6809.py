##########################################################################
#
# Processor specific code

# CPU = "6809"
# Description = "Motorola 6809 8-bit microprocessor."
# DataWidth = 8 # 8-bit data
# AddressWidth = 16 # 16-bit addresses

# Maximum length of an instruction (for formatting purposes)
maxLength = 4

# Leadin bytes for multbyte instructions
leadInBytes = [0x10]

# Addressing mode table
addressModeTable = {
"inherent"    : "",
"imm8"        : "#${0:02X}",
"imm16"       : "#${0:02X}{1:02X}",
"direct"      : "${0:02X}",
"indexed"     : "${0:02X},x",
"extended"    : "${0:02X}{1:02X}",
"rel8"        : "${0:04X}",
"rel16"       : "${0:02X}{1:02X}",
# Extended Indirect
# Relative Indirect
# Zero-offset Indexed
# Zero-offset Indexed Indirect
# Constant-offset Indexed
# Constant-offset Indexed Indirect
# Accumulator-offset Indexed
# Accumulator-offset Indexed Indirect
# Auto-Increment Indexed
# Auto-Increment Indexed Indirect
# Auto-Decrement Indexed
# Auto-Decrement Indexed Indirect
}

# Op Code Table
# Key is numeric opcode (possibly multiple bytes)
# Value is a list:
#   # bytes
#   mnemonic
#   addressing mode.
#   flags (e.g. pcr)
opcodeTable = {

0x3a   :  [ 1, "abx",  "inherent"        ],
0x89   :  [ 2, "adca", "imm8"            ],
0x99   :  [ 2, "adca", "direct"          ],
0xa9   :  [ 2, "adca", "indexed"         ],
0xb9   :  [ 3, "adca", "extended"        ],
0xc9   :  [ 2, "adcb", "imm8"            ],
0xd9   :  [ 2, "adcb", "direct"          ],
0xe9   :  [ 2, "adcb", "indexed"         ],
0xf9   :  [ 3, "adcb", "extended"        ],
0x8b   :  [ 2, "adda", "imm8"            ],
0x9b   :  [ 2, "adda", "direct"          ],
0xab   :  [ 2, "adda", "indexed"         ],
0xbb   :  [ 3, "adda", "extended"        ],
0xcb   :  [ 2, "addb", "imm8"            ],
0xdb   :  [ 2, "addb", "direct"          ],
0xeb   :  [ 2, "addb", "indexed"         ],
0xfb   :  [ 3, "addb", "extended"        ],
0xc3   :  [ 3, "addd", "imm16"           ],
0xd3   :  [ 2, "addd", "direct"          ],
0xe3   :  [ 2, "addd", "indexed"         ],
0xf3   :  [ 3, "addd", "extended"        ],
0x84   :  [ 2, "anda", "imm8"            ],
0x94   :  [ 2, "anda", "direct"          ],
0xa4   :  [ 2, "anda", "indexed"         ],
0xb4   :  [ 3, "anda", "extended"        ],
0xc4   :  [ 2, "andb", "imm8"            ],
0xd4   :  [ 2, "andb", "direct"          ],
0xe4   :  [ 2, "andb", "indexed"         ],
0xf4   :  [ 3, "andb", "extended"        ],
0x1C   :  [ 2, "andcc","imm8"            ],


0x26   :  [ 2, "bne",  "rel8", pcr       ],

0x26   :  [ 2, "bne",  "rel8", pcr       ],

0x1026 :  [ 4, "lbne", "rel16", pcr      ],

0x00   :  [ 2, "neg",  "direct"          ],

0xff   :  [ 3, "stu", "extended"         ],

}

# End of processor specific code
##########################################################################
