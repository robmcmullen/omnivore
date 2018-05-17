#!/bin/bash

python -m cProfile -s cumtime -o cprof.out wxatari.py $*
