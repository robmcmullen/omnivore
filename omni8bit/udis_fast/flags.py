# flags

# udis cpu opcode flags
udis_opcode_flag_branch = 1
udis_opcode_flag_jump = 2
udis_opcode_flag_return = 4
udis_opcode_flag_label = 8
udis_opcode_flag_data_bytes = 16
udis_opcode_flag_store = 32  # is this a store operation? default is load
udis_opcode_flag_undoc = 128

# history flags
flag_branch = 1
flag_jump = 2
flag_rts = 3
flag_rti = 4
flag_origin = 5
flag_data_bytes = 6
flag_write_one = 7
flag_write_two = 8
flag_write_three = 9
flag_valid_target_addr = 32
flag_label = 64
flag_undoc = 128

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
