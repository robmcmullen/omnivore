import os
import glob


def get_latest_file(pathspec):
    files = glob.glob(pathspec)
    if files:
        # for f in files:
        #     print os.path.getctime(f), os.path.getmtime(f), f
        newest = max(files, key=os.path.getmtime)
        return newest
    return pathspec
