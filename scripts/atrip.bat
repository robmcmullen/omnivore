@echo off
rem = """-*-Python-*- script
rem Windows batch script based on pylint's batch scripts
rem Don't know how this works, but it does.
rem
rem -------------------- DOS section --------------------
rem You could set PYTHONPATH or TK environment variables here
python -x "%~f0" %*
goto exit

"""
# -------------------- Python section --------------------
import os,sys

import atrip

atrip.run()

DosExitLabel = """
:exit
rem """
