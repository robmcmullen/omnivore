#!/bin/bash
gcc -shared -fPIC -o sharedLib.so ctypesinfo.c
python ctypesinfo.py
