#!/bin/bash

python cpugen.py
#python disasm_gen.py -a
#cython udis_fast/disasm_speedups.pyx
python disasm_gen.py -a -m
cython udis_fast/disasm_info.pyx udis_fast/disasm_speedups_monolithic.pyx
python setup.py build_ext --inplace
