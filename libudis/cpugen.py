#!/usr/bin/env python
""" Convert udis module level data into a single dictionary structure for all
known processors and save it into cputables.py

"""
import os
import glob

from omni8bit.udis_fast.flags import pcr, und, z80bit, lbl, comment, flag_label, flag_return, flag_jump, flag_branch


# These contain extra info not in udis. Originally they were in udis but they
# haven't been accepted upstream and I don't want to maintain my own version.
# So these strings are appended to the python code as it's read in from udis.

# labelTargets: address modes that reference an address
# Any opcodes that use one of these address modes refer to an absolute
# address in memory, and are a candidate to be replaced by a label

cpu_extra = {
    '6502': """
        labelTargets = set(["absolute", "absolutex", "absolutey", "indirect", "indirectx", "indirecty", "zeropage", "zeropagex", "zeropagey"])
        jumpOpcodes = set(["jmp"])
        branchModes = set(["relative"])
        branchOpcodes = set(["jsr"])
        modesExclude = set(["indirect"])
        returnOpcodes = set(["rts", "rti", "brk"])
        """,
    '65816': """
         labelTargets = set(["absolute", "absolutex", "absolutey", "indirect", "indirectx", "indirecty", "zeropage", "zeropagex", "zeropagey", "indirectzeropage", "absoluteindexedindirect", "absolutelong", "absolutelongx", "absoluteindirectx", "absoluteindirectlong", "directpageindirect", "directpageindirectlong", "directpageindirectlongy", "blockmove"])
         jumpOpcodes = set(["jmp"])
         branchModes = set(["relative", "relativelong"])
         branchOpcodes = set(["jsr"])
         modesExclude = set(["indirect", "absoluteindexedindirect"])
         returnOpcodes = set(["rts", "rti", "brk"])
        """,
    '65c02': """
        labelTargets = set(["absolute", "absolutex", "absolutey", "indirect", "indirectx", "indirecty", "zeropage", "zeropagex", "zeropagey", "absoluteindexedindirect"])
        jumpOpcodes = set(["jmp"])
        branchModes = set(["relative", "relativelong"])
        branchOpcodes = set(["jsr"])
        modesExclude = set(["indirect", "absoluteindexedindirect"])
        returnOpcodes = set(["rts", "rti", "brk"])
        """,
    '6800': """
        labelTargets = set(["direct", "indexed", "extended"])
        jumpOpcodes = set(["jmp"])
        branchModes = set(["relative"])
        branchOpcodes = set(["jsr"])
        modesExclude = set(["indexed"])
        returnOpcodes = set(["rts", "rti"])
        """,
    '6809': """
        labelTargets = set(["direct", "indexed", "extended"])
        jumpOpcodes = set(["jmp"])
        branchModes = set(["rel8", "rel16"])
        branchOpcodes = set(["jsr"])
        modesExclude = set(["indexed"])
        returnOpcodes = set(["rts", "rti"])
        """,
    '6811': """
        labelTargets = set(["direct", "direct2", "direct3", "extended", "indexedx", "indexedx2", "indexedx3", "indexedy", "indexedy2", "indexedy3"])
        """,
    '8051': """
        """,
    '8080': """
        labelTargets = set(["direct"])
        """,
    'z80': """
        labelTargets = set([m for m in list(addressModeTable.keys()) if ",n" in m or ",nn" in m or "indaa" in m or "indn" in m])
        """,
}




def fix_opcode_table(cpu, allow_undoc=False):
    """ Find the NOP opcode and add the 'flag' variable if it doesn't exist so
    calling programs don't have to use a try statement to see if there are 3 or
    4 values in the tuple.
    """
    table = cpu['opcodeTable']
    labels = cpu.get('labelTargets', {})
    jump = cpu.get('jumpOpcodes', set())
    branch = cpu.get('branchOpcodes', set())
    branch_modes = cpu.get('branchModes', set())
    exclude_modes = cpu.get('modesExclude', set())
    ret = cpu.get('returnOpcodes', set())
    possibilities = []
    nop = 0x00
    found_undoc = False
    fixed_table = {}
    for opcode, optable in list(table.items()):
        try:
            length, mnemonic, mode, flag = optable
        except ValueError:
            length, mnemonic, mode = optable
            flag = 0
        if flag & und:
            found_undoc = True
            if not allow_undoc:
                continue
        if mode in labels:
            flag |= flag_label
        if mnemonic in ret:
            flag |= flag_return
        elif mode not in exclude_modes:
            if mnemonic in jump:
                flag |= flag_jump
            elif mnemonic in branch or mode in branch_modes:
                flag |= flag_branch
        fixed_table[opcode] = (length, mnemonic, mode, flag)
        if mnemonic == "nop" and flag == 0:
            nop = opcode
    cpu['opcodeTable'] = fixed_table
    return nop, found_undoc


def read_udis(pathname):
    """ Read all the processor-specific opcode info and pull into a container
    dictionary keyed on the processor name.
    
    The udis files have module level data, so this pulls the data from multiple
    cpus into a single structure that can then be refereced by processor name.
    For example, to find the opcode table in the generated dictionary for the
    6502 processor, use:
    
    cpus['6502']['opcodeTable']
    """
    files = glob.glob("%s/*.py" % pathname)
    cpus = {}
    for filename in files:
        localfile = os.path.basename(filename)
        if filename.endswith("udis.py"):
            continue
        print(f"processing {filename}")
        with open(filename, "r") as fh:
            source = fh.read()
            if "import cputables" in source:
                continue
            if "addressModeTable" in source and "opcodeTable" in source:
                cpu_name, _ = os.path.splitext(localfile)
                g = {"pcr": pcr, "und": und, "z80bit": z80bit, "lbl": lbl, "comment": comment}
                d = {}
                try:
                    extra = cpu_extra[cpu_name]
                except KeyError:
                    pass
                else:
                    source += "\n".join([line.lstrip() for line in extra.splitlines()])
                try:
                    exec(source, g, d)
                    if 'opcodeTable' in d:
                        cpus[cpu_name] = d
                        nop, found_undoc = fix_opcode_table(d, False)
                        cpus[cpu_name]["nop"] = nop
                        if found_undoc:
                            # reload because dict was modified in fix_opcode_table
                            d = {}
                            exec(source, g, d)
                            undoc_cpu_name = "%sundoc" % cpu_name
                            cpus[undoc_cpu_name] = d
                            nop, found_undoc = fix_opcode_table(d, True)
                            cpus[undoc_cpu_name]["nop"] = nop
                except SyntaxError:
                    raise
    return cpus


if __name__ == "__main__":
    import sys
    import argparse
    
    cpudir = os.path.join(os.path.dirname(__file__), "udis")
    destfile = os.path.join(os.path.dirname(__file__), "../omni8bit/udis_fast/cputables.py")

    supported_cpus = read_udis(cpudir)
    output = []
    import pprint
    output.append("# Autogenerated from udis source! Do not edit here, change udis source instead.")
    output.append("processors =\\")
    for line in pprint.pformat(supported_cpus).splitlines():
        output.append(line.strip())
#    print supported_cpus
    with open(destfile, "w") as fh:
        fh.write("\n".join(output))
        fh.write("\n")
