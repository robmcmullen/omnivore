# flags
flag_branch = 1
flag_jump = 2
flag_return = 4
flag_label = 8
flag_data_bytes = 16
flag_store = 32  # is this a store operation? default is load
flag_undoc = 128

flag_origin = flag_jump | flag_return  # jump and return on the same instruction is impossible, so we define it to mean an origin change

pcr = 256 # for all currently defined CPUs: any instruction that uses this flag indicates a branch instruction
und = 512
z80bit = 1024
lbl = 8
comment = 2048
