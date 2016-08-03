#!/bin/bash

rm -rf build/run dist/run; pyinstaller -y --debug --additional-hooks-dir=pyinstaller --windowed run.py
