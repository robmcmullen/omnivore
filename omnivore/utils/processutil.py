import os
import sys
import subprocess
import shlex

def which(program):
    """ find program on system environment path.
    
    From http://stackoverflow.com/questions/377017/
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def run_detach_string(cmdline):
    # don't use posix so it will handle Windows backslash separators
    args = shlex.split(cmdline, posix=False)

    program = which(args[0])
    if program is None:
        raise RuntimeError("%s not found on system path" % args[0])
    args[0] = program
    if sys.platform == "win32":
        p = subprocess.Popen(args, close_fds=True, creationflags=0x00000008|subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        p = subprocess.Popen(args, close_fds=True)
    return p

def run_detach_args(program, args):
    # don't use posix so it will handle Windows backslash separators
    args = shlex.split(args, posix=False)
    args[0:0] = [program]
    
    program = which(program)
    if program is None:
        raise RuntimeError("%s not found on system path" % args[0])
    args[0] = program
    if sys.platform == "win32":
        p = subprocess.Popen(args, close_fds=True, creationflags=0x00000008|subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        p = subprocess.Popen(args, close_fds=True)
    return p
