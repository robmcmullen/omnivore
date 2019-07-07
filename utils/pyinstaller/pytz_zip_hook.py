import os, sys

# get the path to the application, because it may not be the current directory
if getattr(sys, 'frozen', False):
	application_path = os.path.dirname(sys.executable)
elif __file__:
	application_path = os.path.dirname(__file__)

# tell python to use pytz.zip as a source for loading modules
pytz_zip_path = os.path.join(application_path, 'pytz.zip')
sys.path.insert ( 0, pytz_zip_path )
