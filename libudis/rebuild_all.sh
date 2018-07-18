#!/bin/bash

python cpugen.py
#python disasm_gen.py -a
python disasm_gen.py -m
#cython disasm_speedups.pyx
cython disasm_info.pyx disasm_speedups_monolithic.pyx
#python setup.py build_ext --inplace
