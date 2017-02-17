##########################################################################
#
# Processor specific code

# CPU = "Jumpman Level Data"
# Description = "Jumpman Level Data"
# DataWidth = 8  # 8-bit data
# AddressWidth = 16  # 16-bit addresses

# Maximum length of an instruction (for formatting purposes)
maxLength = 4

# Leadin bytes for multibyte instructions
leadInBytes = []

# Addressing mode table
# List of addressing modes and corresponding format strings for operands.
addressModeTable = {
"implicit"    : "",
"type"        : "${1:02X}{0:02X}",
"draw"        : "x=#${0:02X} y=#${1:02X} len=#${2:02X}",
"spacing"     : "dx=#${0:02X} dy=#${1:02X}",
}

# Op Code Table
# Key is numeric opcode (possibly multiple bytes)
# Value is a list:
#   # bytes
#   mnemonic
#   addressing mode
#   flags (e.g. pcr)
opcodeTable = {
0xfc : [ 3, "type",    "type", comment           ],
0xfd : [ 4, "draw",    "draw", comment           ],
0xfe : [ 3, "spacing", "spacing", comment        ],
0xff : [ 1, "end",     "implicit", comment       ],
}

# End of processor specific code
##########################################################################
