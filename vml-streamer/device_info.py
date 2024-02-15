import os

# fix MSMF video capture api slowness on windows!
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'

import subprocess, platform, re, cv2
from PySide6 import QtMultimedia

# get list of available apis using opencv
def getAPIs():
	api_list = [{0:'First available'}]
	for backend in cv2.videoio_registry.getCameraBackends():
		api_list.append({backend:cv2.videoio_registry.getBackendName(backend)})
	return api_list

# checks if ffmpeg is installed and available in the system path
def is_ffmpeg_installed():
	ffmpeg_installed = False
	try:
		out = subprocess.check_output('ffmpeg -version'.split())
		out = out.decode()
		if out.startswith('ffmpeg version'):
			ffmpeg_installed = True
	except:
		pass
	return ffmpeg_installed

# get device list and resolutions using ffmpeg
def getDevicesFFMPEG():
	ffmpeg_format = 'dshow' if platform.system()=='Windows' else 'v4l2'
	ffmpeg_cmd = f'ffmpeg -list_devices true -f {ffmpeg_format} -i dummy'
	proc = subprocess.Popen(ffmpeg_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, unparsed_str = proc.communicate()
	unparsed_str = unparsed_str.decode()

	devices = [
		{
			'id': -1,
			'name': '(none)',
			'resolutions': [],
		}
	]

	if platform.system()=='Windows':

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
				'resolutions': resolutions,
			}

			devices.append(device)

	elif  platform.system()=='Linux':
		pass

	return sorted(devices, key=lambda d: d['id'])

# get device list and resolutions
def getDevicesQT():

	devices = [
		{
			'id': -1,
			'name': '(none)',
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
			'resolutions': resolutions,
		}

		devices.append(device)

	return sorted(devices, key=lambda d: d['id'])

# get device list and resolutions using either ffmpeg or QT (ffmpeg preferred, as QT won't list directshow inputs on windows!)
def getDevices():
	return getDevicesFFMPEG() if is_ffmpeg_installed() else getDevicesQT()

