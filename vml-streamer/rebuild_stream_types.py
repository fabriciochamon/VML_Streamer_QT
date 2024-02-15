import os

files = [f'import {f[0:-3]}' for f in sorted(os.listdir('..')) if f.startswith('st_')]
with open ('../stream_types_import.py', 'w') as f:
	f.write('\n'.join(files))