import os

# fix MSMF video capture api slowness on windows!
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'

import sys, cv2, platform, time, socket, json
import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
from video import VideoThread
import device_info, resources, qt_utils, stream_types

# PyInstaller load splash screen
if getattr(sys, 'frozen', False): import pyi_splash

# Init socket connection (udp)
skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# main UI window widget
class MainWindow(QtWidgets.QWidget):
	def __init__(self):
		super().__init__()

		self.setWindowTitle('VML Streamer')
		self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

		# main layout
		self.layout_main = QtWidgets.QVBoxLayout(self)

		# always on top
		always_on_top = QtWidgets.QCheckBox('Always on top')
		always_on_top.setChecked(True)
		always_on_top.stateChanged.connect(self.AlwaysOnTop)
		
		# show/hide UI groups checkboxes
		self.show_settings = True
		self.current_video_source = 'None'
		check_videosource = QtWidgets.QCheckBox('Source')
		check_videosource.setProperty('class', 'display_UI_group')
		check_videosource.setChecked(True)
		check_videosource.setStyleSheet(qt_utils.getCheckboxVisibilityIconStyleSheet())
		check_videosource.stateChanged.connect(lambda state: self.ShowHideUI(['grp_video_sources'], state==2))

		check_videosettings = QtWidgets.QCheckBox('Settings')
		check_videosettings.setProperty('class', 'display_UI_group')
		check_videosettings.setChecked(True)
		check_videosettings.setStyleSheet(qt_utils.getCheckboxVisibilityIconStyleSheet())
		check_videosettings.stateChanged.connect(lambda state: self.ShowHideUI(['webcam_settings_grp', 'videosettings_grp'], state==2, True))

		check_videofeed = QtWidgets.QCheckBox('Video')
		check_videofeed.setProperty('class', 'display_UI_group')
		check_videofeed.setChecked(True)
		check_videofeed.setStyleSheet(qt_utils.getCheckboxVisibilityIconStyleSheet())
		check_videofeed.stateChanged.connect(lambda state: self.ShowHideUI(['video_feedback','video_info'], state==2))
		
		top_widgets = [always_on_top, 'spacer:20', check_videosource, check_videosettings, check_videofeed]
		qt_utils.addRow(self.layout_main, top_widgets)

		# opencv video thread
		self.VideoThread = VideoThread(source_file=-1)
		self.VideoThread.ImageUpdate.connect(self.ImageUpdate)

		# video sources (buttons)
		video_sources = qt_utils.addVideoSourceButtons(['None', 'Webcam', 'Video file'], caller=self)
		self.layout_main.addWidget(video_sources)

		# webcam settings - group box
		self.webcamsettings_grp = QtWidgets.QGroupBox('Webcam settings')
		self.webcamsettings_grp.setObjectName('webcam_settings_grp')
		self.webcamsettings_grp.hide()
		webcamsettings_widgets = []

		# webcam settings (capture api)
		self.cap_apis = qt_utils.comboFromListOfDict(device_info.getAPIs(), sep_idx=1)
		self.cap_apis.currentIndexChanged.connect(self.ChangeCaptureApi)
		webcamsettings_widgets.extend([QtWidgets.QLabel('Api:'), self.cap_apis])
		
		# webcam settings (device)
		self.devices = device_info.getDevices()
		self.combo_devices = QtWidgets.QComboBox()
		for device in self.devices: self.combo_devices.addItem(device['name'], device['id'])
		self.combo_devices.currentIndexChanged.connect(self.ChangeDevice)
		webcamsettings_widgets.extend([QtWidgets.QLabel('Device:'), self.combo_devices])

		# webcam settings (resolution)
		self.combo_resolutions = QtWidgets.QComboBox()
		self.combo_resolutions.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
		webcamsettings_widgets.extend([QtWidgets.QLabel('Resolution:'), self.combo_resolutions])
		
		# webcam settings (flip image)
		checkbox_flipimage = QtWidgets.QCheckBox()
		checkbox_flipimage.stateChanged.connect(lambda state: self.VideoThread.flip(state==2))
		webcamsettings_widgets.extend([checkbox_flipimage])
		
		# webcam settings - add to main layout
		layout_webcam_settings = QtWidgets.QFormLayout()
		layout_webcam_settings.setLabelAlignment(QtCore.Qt.AlignRight)
		layout_webcam_settings.addRow('Device:', self.combo_devices)
		layout_webcam_settings.addRow('Resolution:', self.combo_resolutions)
		layout_webcam_settings.addRow('Api:', self.cap_apis)
		layout_webcam_settings.addRow('Flip image:', checkbox_flipimage)

		self.webcamsettings_grp.setLayout(layout_webcam_settings)
		self.layout_main.addWidget(self.webcamsettings_grp)

		# video file settings - group box
		self.videosettings_grp = QtWidgets.QGroupBox('Video settings')
		self.videosettings_grp.setObjectName('videosettings_grp')
		self.videosettings_grp.hide()
		videosettings_widgets = []
		layout_video_settings = QtWidgets.QVBoxLayout()

		# video file settings - file path
		self.video_file_label = QtWidgets.QLabel('Path:')
		self.video_file_path = QtWidgets.QLineEdit()
		self.video_file_path.textChanged.connect(self.LoadVideoFromFile)
		self.video_file_path.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
		self.video_file_path.setProperty('class', 'stream_extra_settings')
		self.video_file_path_icon = QtWidgets.QPushButton()
		open_file_pixmap = QtWidgets.QStyle.SP_DialogOpenButton
		icon = self.style().standardIcon(open_file_pixmap)
		self.video_file_path_icon.setIcon(icon)
		self.video_file_path_icon.setProperty('class', 'button-small-padding')
		self.video_file_path_icon.clicked.connect(self.OpenChooseVideoDialog)
		video_file_widgets = [self.video_file_label, self.video_file_path, self.video_file_path_icon]
		videosettings_widgets.extend(video_file_widgets)
		qt_utils.addRow(layout_video_settings, video_file_widgets, add_stretches=False)	

		# video file settings - playback controls	
		self.video_player = qt_utils.VideoPlaybackControls()
		self.video_player.PausePressed.connect(self.VideoThread.pause)
		self.video_player.PlayPressed.connect(self.VideoThread.play)
		self.video_player.FrameChanged.connect(self.GoToFrame)
		self.video_player.FirstFramePressed.connect(self.GoToFirstFrame)
		self.video_player.LastFramePressed.connect(self.GoToLastFrame)
		self.video_player.FlipVideoPressed.connect(lambda state: self.VideoThread.flip(state))
		self.video_player.PlaybackSpeedChanged.connect(lambda speed: self.VideoThread.setPlaybackSpeed(speed))
		self.video_player.SliderPressed.connect(self.VideoThread.pause)
		videosettings_widgets.extend([self.video_player])
		layout_video_settings.addWidget(self.video_player)		

		# video file settings - add to main layout
		self.videosettings_grp.setLayout(layout_video_settings)
		self.layout_main.addWidget(self.videosettings_grp)
		
		# video feedback image
		self.video_feedback = QtWidgets.QLabel()
		self.video_feedback.setObjectName('video_feedback')
		qt_utils.addRow(layout=self.layout_main, widgets=self.video_feedback, centered=True)
		self.video_feedback_width = self.size().width()*0.9

		# video info text (fps,etc)
		self.video_info = QtWidgets.QLabel()
		self.video_info.setProperty('class', 'video_info')
		self.video_info.setObjectName('video_info')
		qt_utils.addRow(layout=self.layout_main, widgets=self.video_info, centered=True)

		# webcam controls (exposure, gain, etc)
		self.cam_autoexposure_label = QtWidgets.QLabel('A')
		self.cam_autoexposure_label.setToolTip('Enable auto exposure')
		self.cam_autoexposure_label.setVisible(False)
		self.cam_autoexposure = QtWidgets.QCheckBox()
		self.cam_autoexposure.stateChanged.connect(lambda state: self.change_cam_autoexposure(state==2))
		self.cam_autoexposure.setVisible(False)
		self.cam_exposure_label = QtWidgets.QLabel('E')
		self.cam_exposure_label.setToolTip('exposure')
		self.cam_exposure_label.setVisible(False)
		self.cam_exposure = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.cam_exposure.sliderReleased.connect(self.change_cam_exposure)
		self.cam_exposure.setVisible(False)
		self.cam_gain_label = QtWidgets.QLabel('G')
		self.cam_gain_label.setToolTip('gain')
		self.cam_gain_label.setVisible(False)
		self.cam_gain = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.cam_gain.sliderReleased.connect(self.change_cam_gain)
		self.cam_gain.setVisible(False)
		self.cam_brightness_label = QtWidgets.QLabel('B')
		self.cam_brightness_label.setToolTip('brightness')
		self.cam_brightness_label.setVisible(False)
		self.cam_brightness = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.cam_brightness.sliderReleased.connect(self.change_cam_brightness)
		self.cam_brightness.setVisible(False)
		self.cam_contrast_label = QtWidgets.QLabel('C')
		self.cam_contrast_label.setToolTip('contrast')
		self.cam_contrast_label.setVisible(False)
		self.cam_contrast = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.cam_contrast.sliderReleased.connect(self.change_cam_contrast)
		self.cam_contrast.setVisible(False)
		webcam_controls_widgets = [
			self.cam_autoexposure_label,
			self.cam_autoexposure,
			self.cam_exposure_label,
			self.cam_exposure,
			self.cam_gain_label,
			self.cam_gain,
			self.cam_brightness_label,
			self.cam_brightness,
			self.cam_contrast_label,
			self.cam_contrast,
		]
		qt_utils.addRow(layout=self.layout_main, widgets=webcam_controls_widgets)

		# streams
		self.streams = []
		btn_add_stream = QtWidgets.QPushButton('+ Add stream')
		btn_add_stream.setProperty('class', 'button-add-stream')
		size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
		btn_add_stream.setSizePolicy(size_policy)
		btn_add_stream.clicked.connect(self.AddStream)
		self.layout_main.addWidget(btn_add_stream)

		# layout stretch bottom
		stretch_layout = QtWidgets.QVBoxLayout()
		stretch_layout.addStretch()
		self.layout_main.addLayout(stretch_layout)

		# init empty video
		self.ChangeVideoSource('None')

		# defined timer (timed calls) for non-video based streams
		self.stream_calls_timer = QtCore.QTimer()
		self.stream_calls_timer.timeout.connect(self.StreamNoVideoInput)
		self.stream_calls_timer.start(30) # in millisecond

	# main window close event
	def closeEvent(self, event):
		self.VideoThread.stop()
		self.VideoThread.wait()
		QtWidgets.QMainWindow.closeEvent(self, event)

	# main window resize event
	def resizeEvent(self, event):
		self.video_feedback_width = event.size().width()*0.9

	# ------------------- #
	#        SLOTS        #
	# ------------------- #
	@QtCore.Slot()
	def ImageUpdate(self, image):

		# run streams
		self.Stream()

		# update video feedback
		vt = self.VideoThread
		resolution = '' if vt.resolution is None else f' @ {vt.resolution[0]}x{vt.resolution[1]}'
		pixmap = QtGui.QPixmap.fromImage(image)
		#pixmap = pixmap.scaledToWidth(self.video_feedback_width)
		self.video_feedback.setPixmap(pixmap)
		self.video_info.setText(f'fps: {vt.fps:.1f} (api: {vt.capture_api_name}){resolution}')

		# update video playback
		player = self.video_player
		if vt.source_type=='video' and not vt.paused:
			player.setFrameCurrent(int(vt.frame), emitSignal=False)
		
	@QtCore.Slot()
	def ChangeVideoSource(self, src):
		self.current_video_source=src

		# none
		if src == 'None':
			self.setVideoEmpty()
			self.videosettings_grp.hide()
			self.webcamsettings_grp.hide()
			self.combo_devices.setCurrentIndex(0)
			self.Display_CamControls(False)

		# webcam
		elif src == 'Webcam':
			self.setVideoEmpty()
			self.videosettings_grp.hide()
			if self.show_settings:
				self.webcamsettings_grp.show()

		# video file
		elif src == 'Video file':
			self.setVideoEmpty()
			self.webcamsettings_grp.hide()
			self.Display_CamControls(False)
			self.combo_devices.setCurrentIndex(0)
			if self.show_settings:
				self.videosettings_grp.show()
			self.LoadVideoFromFile(self.video_file_path.text())

	@QtCore.Slot()
	def ChangeCaptureApi(self, idx):
		self.VideoThread.capture_api = self.cap_apis.itemData(idx)
		self.restartVideo()

	def Display_CamControls(self, bvalue):
		self.cam_autoexposure.setVisible(bvalue)
		self.cam_autoexposure_label.setVisible(bvalue)
		self.cam_exposure.setVisible(bvalue)
		self.cam_exposure_label.setVisible(bvalue)
		self.cam_gain.setVisible(bvalue)
		self.cam_gain_label.setVisible(bvalue)
		self.cam_brightness.setVisible(bvalue)
		self.cam_brightness_label.setVisible(bvalue)
		self.cam_contrast.setVisible(bvalue)
		self.cam_contrast_label.setVisible(bvalue)

	@QtCore.Slot()
	def ChangeDevice(self, idx):

		# build combo resolutions
		chosen_device = [device for device in self.devices if device['id']==self.combo_devices.itemData(idx)][0]
		if chosen_device['id']==-1:
			self.setVideoEmpty()
		else:
			self.combo_resolutions.clear()
			self.combo_resolutions.addItems(chosen_device['resolutions'])
			self.combo_resolutions.currentTextChanged.connect(self.ChangeResolution)
					
			# restart video
			self.VideoThread.source_type = 'webcam'
			self.VideoThread.source_file = chosen_device['id']
			self.VideoThread.resolution = [int(item) for item in self.combo_resolutions.currentText().split('x')]
			self.restartVideo()

			# show camera controls (Linux only!)
			if platform.system() == 'Linux':
				if chosen_device['path'] != '':

					self.Display_CamControls(True)

					ctrls = device_info.get_v4l2_ctrls(chosen_device['path'])
					self.cam_autoexposure.setChecked([x['value'] for x in ctrls if x['name']=='auto_exposure'][0])

					self.cam_exposure.setMinimum([x['min'] for x in ctrls if x['name']=='exposure_time_absolute'][0])
					self.cam_exposure.setMaximum([x['max'] for x in ctrls if x['name']=='exposure_time_absolute'][0])
					self.cam_exposure.setValue([x['value'] for x in ctrls if x['name']=='exposure_time_absolute'][0])

					self.cam_gain.setMinimum([x['min'] for x in ctrls if x['name']=='gain'][0])
					self.cam_gain.setMaximum([x['max'] for x in ctrls if x['name']=='gain'][0])
					self.cam_gain.setValue([x['value'] for x in ctrls if x['name']=='gain'][0])

					self.cam_brightness.setMinimum([x['min'] for x in ctrls if x['name']=='brightness'][0])
					self.cam_brightness.setMaximum([x['max'] for x in ctrls if x['name']=='brightness'][0])
					self.cam_brightness.setValue([x['value'] for x in ctrls if x['name']=='brightness'][0])

					self.cam_contrast.setMinimum([x['min'] for x in ctrls if x['name']=='contrast'][0])
					self.cam_contrast.setMaximum([x['max'] for x in ctrls if x['name']=='contrast'][0])
					self.cam_contrast.setValue([x['value'] for x in ctrls if x['name']=='contrast'][0])

	@QtCore.Slot()
	def ChangeResolution(self, resolution):
		try:
			self.VideoThread.resolution = [int(item) for item in resolution.split('x')]
		except:
			pass
		self.restartVideo()

	@QtCore.Slot()
	def OpenChooseVideoDialog(self):
		formats = ['mp4', 'mov', 'mkv', 'mpg', 'mpeg', 'avi', 'wmv', 'webm']
		formats = ['*.'+f for f in formats]
		fileformats = f'Videos ({" ".join(formats)})'
		filename = QtWidgets.QFileDialog.getOpenFileName(QtWidgets.QFileDialog(), 'Load Video', os.path.expanduser('~'), fileformats)
		self.video_file_path.setText(filename[0])

	@QtCore.Slot()
	def LoadVideoFromFile(self, path):
		if os.path.isfile(path):
			self.VideoThread.source_type = 'video'
			self.VideoThread.source_file = path
			self.VideoThread.paused = False
			self.restartVideo()
			while self.VideoThread.num_frames == -1: time.sleep(0.5)
			self.video_player.setFrameEnd(self.VideoThread.num_frames)
		else:
			self.setVideoEmpty()

	@QtCore.Slot()
	def GoToFrame(self, frame):
		self.VideoThread.frame = frame
		self.VideoThread.forceUpdate()

	@QtCore.Slot()
	def GoToFirstFrame(self):
		self.VideoThread.frame = 1
		self.VideoThread.forceUpdate()

	@QtCore.Slot()
	def GoToLastFrame(self):
		self.VideoThread.frame = self.VideoThread.num_frames
		self.VideoThread.forceUpdate()

	@QtCore.Slot()
	def AlwaysOnTop(self, state):
		if state:
			self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
			self.show()
		else:
			self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
			self.show()

	@QtCore.Slot()
	def AddStream(self):
		new_stream = {
			'id': max([item['id'] for item in self.streams])+1 if len(self.streams) else 0,
			'address': '127.0.0.1',
			'port': max([item['port'] for item in self.streams])+1 if len(self.streams) else 11111,
			'settings': {},
			'needs_video_input': True,
		}
		self.streams.append(new_stream)
		stream_layout = stream_types.getQtWidget(new_stream, self)
		self.layout_main.insertLayout(len(self.layout_main.children())+3, stream_layout)
		combo_type = self.findChild(QtWidgets.QComboBox, f'stream{new_stream["id"]}__comboType')
		self.ChangeStreamType(new_stream['id'], stream_layout, combo_type.currentText())

	@QtCore.Slot()
	def RemoveStream(self, stream_id, widgets, layout):
		
		# remove from streams list
		for i in range(len(self.streams)):
			if self.streams[i]['id']==stream_id:
				del self.streams[i]
				break

		# remove from interface
		for widget in widgets:
			widget.deleteLater()
		layout.layout().deleteLater()
		
	@QtCore.Slot()
	def ChangeStreamType(self, stream_id, stream_layout, chosen_item):
		stream_idx = self.findStreamIndexById(stream_id)
		self.streams[stream_idx]['type'] = chosen_item
		
		# show settings group for chosen type (and hide other groups)
		search_term = f'stream{stream_id}__settings__'
		regex = QtCore.QRegularExpression(f'{search_term}.*')
		grp_invisible = self.findChildren(QtWidgets.QGroupBox, regex, QtCore.Qt.FindChildrenRecursively)
		grp_visible = self.findChild(QtWidgets.QGroupBox, f'{search_term}{chosen_item}', QtCore.Qt.FindChildrenRecursively)
		for grp in grp_invisible: grp.hide()
		if grp_visible is not None: grp_visible.show()

		# update settings in the streams list
		pattern = f'stream{stream_id}__setting__.*__{chosen_item}'		
		regex = QtCore.QRegularExpression(pattern)
		settings = self.findChildren(QtCore.QObject, regex, QtCore.Qt.FindChildrenRecursively)
		
		self.streams[stream_idx]['settings'] = {}
		for s in settings:
			item = s.objectName().split('__')
			setting_name = item[2]
			setting_type = item[3]
			if setting_type == chosen_item:
				if isinstance(s, QtWidgets.QCheckBox):
					self.streams[stream_idx]['settings'][setting_name] = s.isChecked()
				elif isinstance(s, qt_utils.SliderWithNumbers):
					self.streams[stream_idx]['settings'][setting_name] = s.value
				if isinstance(s, QtWidgets.QLineEdit):
					self.streams[stream_idx]['settings'][setting_name] = s.text()
				if isinstance(s, QtWidgets.QComboBox):
					self.streams[stream_idx]['settings'][setting_name] = s.itemData(s.currentIndex())
			else:
				self.streams[stream_idx]['settings'] = {}	

		# update "needs_video_input" stream key
		pattern = f'stream{stream_id}__{chosen_item}__needsVideoInput'		
		regex = QtCore.QRegularExpression(pattern)
		needs_video_input = True
		needs_video_input_checkbox = self.findChildren(QtCore.QObject, regex, QtCore.Qt.FindChildrenRecursively)
		if len(needs_video_input_checkbox): needs_video_input = needs_video_input_checkbox[0].isChecked()
		self.streams[stream_idx]['needs_video_input'] = needs_video_input

	@QtCore.Slot()
	def ChangeStreamAddr(self, address, stream_id):
		self.streams[self.findStreamIndexById(stream_id)]['address'] = address

	@QtCore.Slot()
	def ChangeStreamPort(self, port, stream_id):
		self.streams[self.findStreamIndexById(stream_id)]['port'] = port

	@QtCore.Slot()
	def ChangeStreamSettings(self, stream_id, setting_name, new_value, object_name=None):
		if object_name is not None:
			new_value = self.findChildren(QtCore.QObject, object_name, QtCore.Qt.FindChildrenRecursively)[0].itemData(new_value)
		self.streams[self.findStreamIndexById(stream_id)]['settings'][setting_name] = new_value

	@QtCore.Slot()
	def change_cam_autoexposure(self, value):
		chosen_device = [device for device in self.devices if device['name']==self.combo_devices.currentText()][0]
		device_info.set_v4l2_config(chosen_device['path'], 'auto_exposure', 3 if value else 1)
		ctrls = device_info.get_v4l2_ctrls(chosen_device['path'])
		self.cam_exposure.setValue([x['value'] for x in ctrls if x['name']=='exposure_time_absolute'][0])

	@QtCore.Slot()
	def change_cam_exposure(self):
		value = self.cam_exposure.value()
		chosen_device = [device for device in self.devices if device['name']==self.combo_devices.currentText()][0]
		device_info.set_v4l2_config(chosen_device['path'], 'exposure_time_absolute', value)

	@QtCore.Slot()
	def change_cam_gain(self):
		value = self.cam_gain.value()
		chosen_device = [device for device in self.devices if device['name']==self.combo_devices.currentText()][0]
		device_info.set_v4l2_config(chosen_device['path'], 'gain', value)

	@QtCore.Slot()
	def change_cam_brightness(self):
		value = self.cam_brightness.value()
		chosen_device = [device for device in self.devices if device['name']==self.combo_devices.currentText()][0]
		device_info.set_v4l2_config(chosen_device['path'], 'brightness', value)

	@QtCore.Slot()
	def change_cam_contrast(self):
		value = self.cam_contrast.value()
		chosen_device = [device for device in self.devices if device['name']==self.combo_devices.currentText()][0]
		device_info.set_v4l2_config(chosen_device['path'], 'contrast', value)
		
	@QtCore.Slot()
	def ShowHideUI(self, widget_names, state, isSettings=False):
		if isSettings: self.show_settings = state

		for name in widget_names:
			widget = self.findChild(QtCore.QObject, name)
			if widget is not None: 
				if state: 
					if isSettings:
						if self.current_video_source!='None':
							if name == 'webcam_settings_grp' and self.current_video_source == 'Webcam': widget.show()
							if name == 'videosettings_grp' and self.current_video_source == 'Video file': widget.show()
					else:
						widget.show()
				else: 
					widget.hide()

	def findStreamIndexById(self, _id):
		ret = None
		for i, stream in enumerate(self.streams):
			if stream['id']==_id:
				ret = i
				break
		return ret
		
	def restartVideo(self):
		self.VideoThread.stop()
		while not self.VideoThread.stopped: time.sleep(0.5)
		self.VideoThread.start()

	def setVideoEmpty(self):
		self.VideoThread.stop()
		self.VideoThread.fps = 0
		self.VideoThread.frameCounter = 0
		self.ImageUpdate(QtGui.QImage(resources.getPath('images/no_video.png')))
		self.video_info.setText(f'fps: 0.0 (api: none)')

	def Stream(self, video_based=True):
		filtered_streams = [x for x in self.streams if x['needs_video_input']==video_based]
		if not video_based or (video_based and self.VideoThread.imageRGB is not None):			
			for stream in filtered_streams:				
				data = stream_types.getProcessors()[stream['type']].run(self.VideoThread, stream, self.streams)
				stream_idx = [i for i, x in enumerate(self.streams) if x['id']==stream['id']][0]
				self.streams[stream_idx]['data'] = data
				
				if data is not None:
					addr_port = (stream['address'], stream['port'])

					# send dicts
					if isinstance(data, dict):
						skt.sendto(json.dumps(data).encode(), addr_port)

					# send numpy arrays
					elif isinstance(data, np.ndarray):
						skt.sendto(data.tobytes(), addr_port)

	@QtCore.Slot()
	def StreamNoVideoInput(self):
		if len(self.streams): self.Stream(video_based=False)
			
# main program
if __name__ == '__main__':
	app = QtWidgets.QApplication([])
	
	# set app font size
	font = QtGui.QFont()
	font.setPointSize(8)
	app.setFont(font)

	# apply stylesheet
	stylesheet_path = resources.getPath('stylesheet.qss')
	with open(stylesheet_path, 'r') as stylesheet_file:
		app.setStyleSheet(stylesheet_file.read())

	# update splash screen text
	if getattr(sys, 'frozen', False): pyi_splash.update_text('Fetching available webcam devices...')

	# init QT main window
	win = MainWindow()
	win.resize(350, 750)
	
	# PyInstaller close splash screen
	if getattr(sys, 'frozen', False): pyi_splash.close()
	
	# show main window
	win.show()
	sys.exit(app.exec())
