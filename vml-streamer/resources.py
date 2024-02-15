import sys
from pathlib import Path

#---------------------------------------------------------#
# this is to facilitate building binaries with pyinstaller
#---------------------------------------------------------#

# get path relative to .py file (if running from venv) OR
# get path relative to tmp directory (extracted files) if running from binary
def getPath(relative_path):
	if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
		bundle_dir = Path(sys._MEIPASS)
	else:
		bundle_dir = Path(__file__).parent

	bundle_dir = str(bundle_dir).replace('\\', '/')
	resource_path = f'{bundle_dir}/{relative_path}'
	
	return resource_path