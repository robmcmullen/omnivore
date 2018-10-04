# flags

# udis cpu opcode flags
udis_opcode_flag_branch = 1
udis_opcode_flag_jump = 2
udis_opcode_flag_return = 4
udis_opcode_flag_label = 8
udis_opcode_flag_data_bytes = 16
udis_opcode_flag_store = 32  # is this a store operation? default is load
udis_opcode_flag_undoc = 128

# flags
FLAG_BRANCH_TAKEN = 1
FLAG_BRANCH_NOT_TAKEN = 2
FLAG_JUMP = 3
FLAG_RTS = 4
FLAG_RTI = 5
FLAG_ORIGIN = 6
FLAG_DATA_BYTES = 7
FLAG_WRITE_ONE = 8
FLAG_WRITE_TWO = 9
FLAG_WRITE_THREE = 10
FLAG_READ_ONE = 11
FLAG_REPEATED_BYTES = 12
FLAG_TARGET_ADDR = 32
FLAG_LABEL = 64
FLAG_UNDOC = 128

# disassembler types
DISASM_DATA = 0
DISASM_6502 = 10
DISASM_65816 = 12
DISASM_65C02 = 13
DISASM_6800 = 14
DISASM_6809 = 15
DISASM_6811 = 16
DISASM_8051 = 17
DISASM_8080 = 18
DISASM_Z80 = 19
DISASM_ANTIC_DL = 30
DISASM_JUMPMAN_HARVEST = 31
DISASM_JUMPMAN_LEVEL = 32
DISASM_FRAME_START = 128
DISASM_FRAME_START_RESULT = 129
DISASM_FRAME_END = 130
DISASM_FRAME_END_RESULT = 131
DISASM_6502_HISTORY = 132
DISASM_6502_HISTORY_RESULT = 133
DISASM_ATARI800_HISTORY = 134
DISASM_ATARI800_HISTORY_RESULT = 135

udis_opcode_flag_map = {
    udis_opcode_flag_branch: "FLAG_BRANCH",
    udis_opcode_flag_jump: "FLAG_JUMP",
    udis_opcode_flag_return: "FLAG_RTS",
    udis_opcode_flag_label: "FLAG_LABEL",
    udis_opcode_flag_undoc: "FLAG_UNDOC",
}

pcr = 256 # for all currently defined CPUs: any instruction that uses this flag indicates a branch instruction
und = 512
z80bit = 1024
lbl = 8
comment = 2048
