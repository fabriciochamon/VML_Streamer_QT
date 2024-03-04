from PySide6 import QtCore, QtWidgets, QtGui
import resources

# put widgets in a row and add to a parent layout
def addRow(layout=None, widgets=None, centered=False, add_stretches=True):
	ret = None
	if widgets is not None:
		if not isinstance(widgets, list):
			widgets = [widgets]
		hlayout = QtWidgets.QHBoxLayout()
		if centered and add_stretches: hlayout.addStretch()
		for widget in widgets:
			if isinstance(widget, str):
				hlayout.addSpacing(int(widget.split(':')[1]))
			else:
				hlayout.addWidget(widget)
		if add_stretches: hlayout.addStretch()
		if layout is not None: layout.addLayout(hlayout)
		ret = hlayout
	return ret

# creates a combo box with item text + item data, based on a list of single entry dicts
# where item data = dict key and item text = dict value
def comboFromListOfDict(list_items=[], sep_idx=None):
	combo = QtWidgets.QComboBox()
	for item in list_items:
		k, v = list(item.items())[0]
		combo.addItem(item[k], k)
	if sep_idx: combo.insertSeparator(sep_idx)
	return combo

# adds a group box with video sources as checkable push buttons
# "clicked" signal emits the label string itself
def addVideoSourceButtons(labels=[], caller=None, css_class='button-orange'):
	vs_grp = QtWidgets.QGroupBox('Video source')
	vs_grp.setObjectName('grp_video_sources')
	vs_btn_labels = labels
	vs_buttons = []
	for i, button_label in enumerate(vs_btn_labels):
		btn = QtWidgets.QPushButton(button_label)
		btn.setCheckable(True)
		btn.setAutoExclusive(True)
		if i==0: btn.setChecked(True)
		btn.setProperty('class', css_class)
		btn.clicked.connect(lambda checked=None, src=button_label: caller.ChangeVideoSource(src))
		vs_buttons.append(btn)
	vs_grp.setLayout(addRow(widgets=vs_buttons, add_stretches=False))
	return vs_grp


# a slider that shows min/max/current values
class SliderWithNumbers(QtWidgets.QWidget):
	ValueChanged = QtCore.Signal(float)

	def __init__(self, min_val=0, max_val=100, default_val=0, units=''):
		super().__init__()

		vlayout = QtWidgets.QVBoxLayout()
		hlayout_slider = QtWidgets.QHBoxLayout()
		hlayout_numbers = QtWidgets.QHBoxLayout()
		margins = QtCore.QMargins()
		margins.setTop(0)
		self.units = units
		self.min = QtWidgets.QLabel(f'{str(min_val)} {units}')
		self.min.setContentsMargins(margins)
		self.max = QtWidgets.QLabel(f'{str(max_val)} {units}')
		self.max.setContentsMargins(margins)
		self.val = QtWidgets.QLabel(f'{str(default_val*10/10)} {units}')
		self.val.setContentsMargins(margins)
		self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.slider.setMinimum(min_val*10)
		self.slider.setMaximum(max_val*10)
		self.slider.setValue(default_val*10)
		self.slider.valueChanged.connect(self.UpdateCurrentValue)
		self.slider.sliderReleased.connect(self.SliderReleased)
		hlayout_slider.addWidget(self.slider)
		hlayout_numbers.addWidget(self.min)
		hlayout_numbers.addStretch()
		hlayout_numbers.addWidget(self.val)
		hlayout_numbers.addStretch()
		hlayout_numbers.addWidget(self.max)
		hlayout_numbers.setContentsMargins(margins)
		vlayout.addLayout(hlayout_slider)
		vlayout.addLayout(hlayout_numbers)
		self.setLayout(vlayout)
		self.value = default_val


	@QtCore.Slot()
	def UpdateCurrentValue(self, value):
		self.value = value/10
		self.val.setText(f'{str(self.value)} {self.units}')

	@QtCore.Slot()
	def SliderReleased(self):
		self.value = self.slider.value()/10
		self.ValueChanged.emit(self.value)
		

# video playback controls
class VideoPlaybackControls(QtWidgets.QWidget):
	PlayPressed = QtCore.Signal()
	PausePressed = QtCore.Signal()
	FirstFramePressed = QtCore.Signal()
	LastFramePressed = QtCore.Signal()
	FrameChanged = QtCore.Signal(int)
	FlipVideoPressed = QtCore.Signal(bool)
	PlaybackSpeedChanged = QtCore.Signal(float)
	SliderPressed = QtCore.Signal()

	def __init__(self):
		super().__init__()

		hlayout_main = QtWidgets.QHBoxLayout()
		vlayout_buttons = QtWidgets.QVBoxLayout()
		hlayout_buttons = QtWidgets.QHBoxLayout()
		margins = QtCore.QMargins()
		margins.setTop(0)
		margins.setBottom(0)

		# icons
		icon_firstFrame = QtWidgets.QStyle.SP_MediaSkipBackward
		icon_lastFrame = QtWidgets.QStyle.SP_MediaSkipForward
		icon_play = QtWidgets.QStyle.SP_MediaPlay
		icon_pause = QtWidgets.QStyle.SP_MediaPause

		# buttons		
		btn_firstFrame = QtWidgets.QPushButton()
		btn_firstFrame.setToolTip('Go to First Frame')
		btn_firstFrame.setIcon(self.style().standardIcon(icon_firstFrame))
		btn_firstFrame.setProperty('class', 'button-playback-controls')
		btn_firstFrame.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
		btn_firstFrame.clicked.connect(lambda: self.FirstFramePressed.emit())
		btn_firstFrame.clicked.connect(lambda: self.setFrameCurrent(self.firstFrame))
		hlayout_buttons.addWidget(btn_firstFrame)

		btn_pause = QtWidgets.QPushButton()
		btn_pause.setToolTip('Pause Video')
		btn_pause.setIcon(self.style().standardIcon(icon_pause))
		btn_pause.setProperty('class', 'button-playback-controls')
		btn_pause.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
		btn_pause.clicked.connect(lambda: self.PausePressed.emit())
		hlayout_buttons.addWidget(btn_pause)

		btn_play = QtWidgets.QPushButton()
		btn_play.setToolTip('Play Video')
		btn_play.setIcon(self.style().standardIcon(icon_play))
		btn_play.setProperty('class', 'button-playback-controls')
		btn_play.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
		btn_play.clicked.connect(lambda: self.PlayPressed.emit())
		hlayout_buttons.addWidget(btn_play)

		btn_lastFrame = QtWidgets.QPushButton()
		btn_lastFrame.setToolTip('Go to Last Frame')
		btn_lastFrame.setIcon(self.style().standardIcon(icon_lastFrame))
		btn_lastFrame.setProperty('class', 'button-playback-controls')
		btn_lastFrame.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
		btn_lastFrame.clicked.connect(lambda: self.LastFramePressed.emit())
		btn_lastFrame.clicked.connect(lambda: self.setFrameCurrent(self.lastFrame))
		hlayout_buttons.addWidget(btn_lastFrame)

		vlayout_buttons.addLayout(hlayout_buttons)
		vlayout_buttons.setAlignment(QtCore.Qt.AlignTop)

		hlayout_main.addLayout(vlayout_buttons)

		# timeline slider
		vlayout_timeline = QtWidgets.QVBoxLayout()
		vlayout_timeline.setAlignment(QtCore.Qt.AlignTop)
		hlayout_slider = QtWidgets.QHBoxLayout()
		hlayout_numbers = QtWidgets.QHBoxLayout()
		hlayout_numbers.setAlignment(QtCore.Qt.AlignTop)
		self.min = QtWidgets.QLabel('1')
		self.min.setContentsMargins(margins)
		self.max = QtWidgets.QLabel('1')
		self.max.setContentsMargins(margins)
		self.val = QtWidgets.QLineEdit('1')
		self.val.setContentsMargins(margins)
		self.val.setAlignment(QtCore.Qt.AlignCenter)
		self.val.editingFinished.connect(lambda: self.setFrameCurrent(self.val.text()))

		# set frame input width to defined num chars
		nchars = 6
		fm = self.val.fontMetrics()
		m = self.val.textMargins()
		c = self.val.contentsMargins()
		w = nchars*fm.boundingRect('0').width()+m.left()+m.right()+c.left()+c.right()
		self.val.setMaximumWidth(w+8)

		self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		self.slider.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
		self.slider.setMinimum(1)
		self.slider.setMaximum(1)
		self.slider.setValue(1)
		self.slider.valueChanged.connect(self.SliderUpdateCurrentFrame)
		self.slider.sliderPressed.connect(lambda: self.SliderPressed.emit())
		hlayout_slider.addWidget(self.slider)
		hlayout_numbers.addWidget(self.min)
		hlayout_numbers.addStretch()
		hlayout_numbers.addWidget(self.val)
		hlayout_numbers.addStretch()
		hlayout_numbers.addWidget(self.max)
		hlayout_numbers.setContentsMargins(margins)
		vlayout_timeline.addLayout(hlayout_slider)
		vlayout_timeline.addLayout(hlayout_numbers)

		# flip video
		flipVideo = QtWidgets.QCheckBox('Flip video')
		flipVideo.stateChanged.connect(lambda state: self.FlipVideoPressed.emit(state==2))
		vlayout_buttons.addWidget(flipVideo)

		# set layout hierarchy
		hlayout_main.addLayout(vlayout_timeline)
		vlayout_main = QtWidgets.QVBoxLayout()
		vlayout_main.addLayout(hlayout_main)

		# video playback speed
		hlayout_video_speed = QtWidgets.QHBoxLayout()
		self.slider_video_speed = SliderWithNumbers(1, 10, 1, units='x')
		self.slider_video_speed.ValueChanged.connect(lambda value: self.PlaybackSpeedChanged.emit(value))
		hlayout_video_speed.addWidget(QtWidgets.QLabel('Playback speed:'))
		hlayout_video_speed.addWidget(self.slider_video_speed)
		vlayout_main.addLayout(hlayout_video_speed)
		
		# set main layout
		self.setLayout(vlayout_main)

		# init timeline
		self.currentFrame = 1
		self.firstFrame = 1
		self.lastFrame = 1
		

	def setFrameStart(self, value):
		self.firstFrame = int(value)
		self.min.setText(str(self.firstFrame))

	def setFrameEnd(self, value):
		self.lastFrame = int(value)
		self.max.setText(str(self.lastFrame))
		self.slider.setMaximum(self.lastFrame)

	def setFrameCurrent(self, value, emitSignal=True):
		emit = False
		value = int(value) if str(value).isnumeric() else self.currentFrame
		if value<=self.lastFrame or value>=self.firstFrame:
			self.currentFrame = value
			emit = True
		self.val.setText(str(self.currentFrame))
		self.slider.setValue(self.currentFrame)
		if emit and emitSignal: self.FrameChanged.emit(self.currentFrame)

	@QtCore.Slot()
	def SliderUpdateCurrentFrame(self, value):
		self.currentFrame = value
		self.val.setText(str(self.currentFrame))
		self.FrameChanged.emit(self.currentFrame)


# return css to set visibility checkboxes icons
def getCheckboxVisibilityIconStyleSheet():
	eyeON = resources.getPath('./images/eye-on.png')
	eyeOFF = resources.getPath('./images/eye-off.png')
	eyeHOVER = resources.getPath('./images/eye-hover.png')

	style  = '.display_UI_group::indicator:checked{image: url('+eyeON+');}'
	style += '.display_UI_group::indicator:unchecked{image: url('+eyeOFF+');}'
	style += '.display_UI_group::indicator:checked:hover{image: url('+eyeHOVER+');}'
	style += '.display_UI_group::indicator:unchecked:hover{image: url('+eyeHOVER+');}'

	style += '.display_UI_group{font-size: 8pt;}'

	return style