import os

# fix MSMF video capture api slowness on windows!
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'

import subprocess, platform, re, cv2
from PySide6 import QtMultimedia

# global vars
DEVICE_LIST       = None
V4L2_AVAILABLE    = None
FFMPEG_AVAILABLE  = None

# get list of available apis using opencv
def getAPIs():
	api_list = [{0:'First available'}]
	for backend in cv2.videoio_registry.getCameraBackends():
		api_list.append({backend:cv2.videoio_registry.getBackendName(backend)})
	return api_list

# checks if ffmpeg is installed and available in the system path
def is_ffmpeg_installed():
	global FFMPEG_AVAILABLE

	if not FFMPEG_AVAILABLE:
		ffmpeg_installed = False
		try:
			out = subprocess.check_output('ffmpeg -version'.split())
			out = out.decode()
			if out.startswith('ffmpeg version'):
				ffmpeg_installed = True
		except:
			pass
		
		FFMPEG_AVAILABLE = ffmpeg_installed

	return FFMPEG_AVAILABLE

# checks if v4l2 is available in the system path
def is_v4l2_available():
	global V4L2_AVAILABLE

	if not V4L2_AVAILABLE:
		v4l_available = False
		try:
			out = subprocess.check_output('v4l2-ctl --version'.split())
			out = out.decode()
			if out.startswith('v4l2-ctl'):
				v4l_available = True
		except:
			pass
		V4L2_AVAILABLE = v4l_available

	return V4L2_AVAILABLE


# get device list and resolutions using v4l2 (linux)
def getDevicesV4L2():
	v4l2_cmd = 'v4l2-ctl --list-devices'
	out = subprocess.check_output(v4l2_cmd.split())
	unparsed_str = out.decode()
	items = unparsed_str.split('\n\n')

	devices = [
		{
			'id': -1,
			'name': '(none)',
			'path': '',
			'resolutions': [],
		}
	]

	for item in items:
		device_name = item.split(':')[0].split('(')[0].strip()
		if device_name!='':

			device_path = item.split('\n\t')[1]
			device_id = device_path.split('/')[-1]
			device_id = int(''.join([x for x in device_id if x.isnumeric()]))

			v4l2_cmd = f'v4l2-ctl -d {device_path} --list-formats-ext'
			out = subprocess.check_output(v4l2_cmd.split())
			unparsed_str = out.decode()
			patternRes = re.compile(r'.*Size: Discrete (\d*x\d*)')
			resolutions = patternRes.findall(unparsed_str)
			resolutions = list(set(resolutions))
			resolutions = sorted(resolutions, key=lambda x: int(x.split('x')[0]))
			
			if len(resolutions):
				device = {
					'id': device_id,
					'name': device_name,
					'path': device_path,
					'resolutions': resolutions,
				}

				devices.append(device)

	return sorted(devices, key=lambda d: d['id'])
			

# get device list and resolutions using ffmpeg
def getDevicesFFMPEG():
	ffmpeg_format = 'dshow'
	ffmpeg_cmd = f'ffmpeg -list_devices true -f {ffmpeg_format} -i dummy'
	proc = subprocess.Popen(ffmpeg_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, unparsed_str = proc.communicate()
	unparsed_str = unparsed_str.decode()

	devices = [
		{
			'id': -1,
			'name': '(none)',
			'path': '',
			'resolutions': [],
		}
	]

	
	unparsed_str = unparsed_str.split('DirectShow audio devices')[0]
	pattern = re.compile(r'\[dshow @ .*\]  \"(.*)\".*\n')
	
	for i, item in enumerate(pattern.findall(unparsed_str)):
		
		# get available resolutions
		ffmpeg_cmd = f'ffmpeg -list_options true -f {ffmpeg_format} -i '.split()
		ffmpeg_cmd.extend([f'video={item}'])
		proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, unparsed_str = proc.communicate()
		unparsed_str = unparsed_str.decode()
		patternMinRes = re.compile(r'.*min s=(\d*x\d*)')
		patternMaxRes = re.compile(r'.*max s=(\d*x\d*)')
		resolutions = patternMinRes.findall(unparsed_str)
		resolutions.extend(patternMaxRes.findall(unparsed_str))
		resolutions = list(set(resolutions))
		resolutions = sorted(resolutions, key=lambda x: int(x.split('x')[0]))

		device = {
			'id': i,
			'name': item,
			'path': '',
			'resolutions': resolutions,
		}

		devices.append(device)

	return sorted(devices, key=lambda d: d['id'])

# get device list and resolutions
def getDevicesQT():

	devices = [
		{
			'id': -1,
			'name': '(none)',
			'path': '',
			'resolutions': [],
		}
	]

	device_list = QtMultimedia.QMediaDevices()
	video_inputs = device_list.videoInputs()
	for i, video_input in enumerate(video_inputs):

		video_formats = video_input.videoFormats()
		resolutions = [f'{item.resolution().width()}x{item.resolution().height()}' for item in video_formats]
		resolutions = list(set(resolutions))
		resolutions = sorted(resolutions, key=lambda x: int(x.split('x')[0]))

		device = {
			'id': i,
			'name': video_input.description(),
			'path': '',
			'resolutions': resolutions,
		}

		devices.append(device)

	return sorted(devices, key=lambda d: d['id'])

# get device list and resolutions using either ffmpeg or QT (ffmpeg preferred, as QT won't list directshow inputs on windows!)
def getDevices():
	global DEVICE_LIST
	
	if not DEVICE_LIST:
		devices = []
		if platform.system()=='Windows':
			devices = getDevicesFFMPEG() if is_ffmpeg_installed() else getDevicesQT()

		elif platform.system()=='Linux':
			devices = getDevicesV4L2() if is_v4l2_available() else getDevicesQT()

		DEVICE_LIST = devices

	return DEVICE_LIST

# set webcam values using v4l2
def set_v4l2_config(device_path, ctrl, val):
	cmd = f'v4l2-ctl -d {device_path} --set-ctrl {ctrl}={val}'
	subprocess.call(cmd.split())

# get webcam values using v4l2
def get_v4l2_ctrls(device_path):
	controls = []
	cmd = f'v4l2-ctl -d {device_path} -l'
	out = subprocess.check_output(cmd.split())
	unparsed_str = out.decode()
	if 'Camera Controls' in unparsed_str:
		ctrl_names = ['auto_exposure', 'exposure_time_absolute', 'gain', 'brightness', 'contrast']
		for name in ctrl_names:
			line = [item for item in unparsed_str.split('\n') if item.strip().startswith(name)]
			if len(line):
				line = line[0]
				minimum = line.split('min=')[1].split(' ')[0]
				maximum = line.split('max=')[1].split(' ')[0]
				value   = line.split('value=')[1].split(' ')[0]
				value = float(value)
				if name == 'auto_exposure':
					value = False if value==1 else True

				ctrl = {
					'name': name,
					'min': float(minimum),
					'max': float(maximum),
					'value': value,
				}
				controls.append(ctrl)
	return controls
