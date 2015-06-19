##########################################################################
#
# Processor specific code

# CPU = "6811"
# Description = "FreeScale 68HC11 8-bit microcontroller."
# DataWidth = 8 # 8-bit data
# AddressWidth = 16 # 16-bit addresses

# Maximum length of an instruction (for formatting purposes)
maxLength = 5;

# Leadin bytes for multbyte instructions
leadInBytes = [0x18, 0x1a, 0xcd]

# Addressing mode table
addressModeTable = {
"inherent"   : "",
"immediate"  : "#${0:02X}",
"immediatex" : "#${0:02X}{1:02X}",
"direct"     : "${0:02X}",
"extended"   : "${0:02X}{1:02X}",
"indexedx"   : "${0:02X},X",
"indexedy"   : "${0:02X},Y",
"relative"   : "${0:04X}",
}

# Op Code Table
# Key is numeric opcode (possibly multiple bytes)
# Value is a list:
#   # bytes
#   mnemonic
#   addressing mode.
#   flags (e.g. pcr)
opcodeTable = {

0x1b   :  [ 1, "aba",  "inherent"        ],
0x3a   :  [ 1, "abx",  "inherent"        ],
0x183a :  [ 2, "aby",  "inherent"        ],
0x89   :  [ 2, "adca", "immediate"       ],
0x99   :  [ 2, "adca", "direct"          ],
0xb9   :  [ 3, "adca", "extended"        ],
0xa9   :  [ 2, "adca", "indexedx"        ],
0x18a9 :  [ 3, "adca", "indexedy"        ],
0xc9   :  [ 2, "adcb", "immediate"       ],
0xd9   :  [ 2, "adcb", "direct"          ],
0xf9   :  [ 3, "adcb", "extended"        ],
0xe9   :  [ 2, "adcb", "indexedx"        ],
0x18e9 :  [ 3, "adcb", "indexedy"        ],
0x8b   :  [ 2, "adda", "immediate"       ],
0x9b   :  [ 2, "adda", "direct"          ],
0xbb   :  [ 3, "adda", "extended"        ],
0xab   :  [ 2, "adda", "indexedx"        ],
0x18ab :  [ 3, "adda", "indexedy"        ],
0xcb   :  [ 2, "addb", "immediate"       ],
0xdb   :  [ 2, "addb", "direct"          ],
0xfb   :  [ 3, "addb", "extended"        ],
0xeb   :  [ 2, "addb", "indexedx"        ],
0x18eb :  [ 3, "addb", "indexedy"        ],
0xc3   :  [ 3, "addd", "immediatex"      ],
0xd3   :  [ 2, "addd", "direct"          ],
0xf3   :  [ 3, "addd", "extended"        ],
0xe3   :  [ 2, "addd", "indexedx"        ],
0x18e3 :  [ 3, "addd", "indexedy"        ],
0x84   :  [ 2, "anda", "immediate"       ],
0x94   :  [ 2, "anda", "direct"          ],
0xb4   :  [ 3, "anda", "extended"        ],
0xa4   :  [ 2, "anda", "indexedx"        ],
0x18a4 :  [ 3, "anda", "indexedy"        ],
0xc4   :  [ 2, "andb", "immediate"       ],
0xd4   :  [ 2, "andb", "direct"          ],
0xf4   :  [ 3, "andb", "extended"        ],
0xe4   :  [ 2, "andb", "indexedx"        ],
0x18e4 :  [ 3, "andb", "indexedy"        ],
0x78   :  [ 3, "asl",  "extended"        ],
0x68   :  [ 2, "asl",  "indexedx"        ],
0x1868 :  [ 3, "asl",  "indexedy"        ],
0x48   :  [ 1, "asla", "inherent"        ],
0x58   :  [ 1, "aslb", "inherent"        ],
0x05   :  [ 1, "asld", "inherent"        ],
0x77   :  [ 3, "asr",  "extended"        ],
0x67   :  [ 2, "asr",  "indexedx"        ],
0x1867 :  [ 3, "asr",  "indexedy"        ],
0x47   :  [ 1, "asra", "inherent"        ],
0x57   :  [ 1, "asrb", "inherent"        ],
0x24   :  [ 2, "bcc",  "relative", pcr   ],



0x00   :  [ 1, "test", "inherent"        ],
0x01   :  [ 1, "nop",  "inherent"        ],
0x02   :  [ 2, "ora",  "direct"          ],
0x03   :  [ 3, "jmp",  "extended"        ],
0x20   :  [ 2, "bra",  "relative", pcr   ],
0x86   :  [ 2, "ldaa", "immediate"       ],
0x8f   :  [ 1, "xgdx", "inherent"        ],
0x188f :  [ 2, "xgdy", "inherent"        ],

}

# End of processor specific code
##########################################################################
