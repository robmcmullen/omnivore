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
FLAG_REPEATED_BYTES = 3
FLAG_REG_A = 4
FLAG_REG_X = 5
FLAG_REG_Y = 6
FLAG_LOAD_A_FROM_MEMORY = 7
FLAG_LOAD_X_FROM_MEMORY = 8
FLAG_LOAD_Y_FROM_MEMORY = 9
FLAG_MEMORY_ALTER = 10
FLAG_MEMORY_READ_ALTER_A = 11 
FLAG_PEEK_MEMORY = 12
FLAG_PULL_A = 13
FLAG_PULL_SR = 14
FLAG_PUSH_A = 15
FLAG_PUSH_SR = 16
FLAG_RTI = 17
FLAG_RTS = 18
FLAG_STORE_A_IN_MEMORY = 19
FLAG_STORE_X_IN_MEMORY = 20
FLAG_STORE_Y_IN_MEMORY = 21
FLAG_TARGET_ADDR = 64
FLAG_REG_SR = 128

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

# types 128-191 are for history entries that have result entries
DISASM_6502_HISTORY = 128
DISASM_6502_HISTORY_RESULT = 129
DISASM_ATARI800_HISTORY = 130
DISASM_ATARI800_HISTORY_RESULT = 131
DISASM_NEXT_INSTRUCTION = 132
DISASM_NEXT_INSTRUCTION_RESULT = 133

# types 192-254 don't have results
DISASM_FRAME_START = 192
DISASM_FRAME_END = 193
DISASM_ATARI800_VBI_START = 194
DISASM_ATARI800_VBI_END = 195
DISASM_ATARI800_DLI_START = 196
DISASM_ATARI800_DLI_END = 197

DISASM_BREAKPOINT = 253
DISASM_USER_DEFINED = 254
DISASM_UNKNOWN = 255

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
