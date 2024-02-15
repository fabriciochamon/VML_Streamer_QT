import os

# fix MSMF video capture api slowness on windows!
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'

import cv2, time
from PySide6 import QtCore, QtWidgets, QtGui

class VideoThread(QtCore.QThread):
	ImageUpdate = QtCore.Signal(QtGui.QImage)
	
	def __init__(self, source_type='webcam', source_file=0, capture_api=cv2.CAP_ANY, resolution=None):
		super().__init__()
		self.source_type = source_type
		self.source_file = source_file
		self.capture_api = capture_api
		self.capture_api_name = 'none'
		self.resolution = resolution
		self.fps = 0
		self.source_fps = 24
		self.frame = 1
		self.num_frames = -1
		self.paused = False
		self.stopped = True
		self.speed = 1
		self.cvframe = None		
		self.imageBGR = None
		self.imageRGB = None
		self.imageDISPLAY = None
		self.imageQT = None		
		self.flipImage = False
		self.pos_msec = 0
		self.last_frame_update_time = time.time()
		self.video_needs_frame_update = True
		self.frameCounter = 0

	# flip image horizontally
	def flip(self, doFlip):
		self.flipImage = doFlip
		self.forceUpdate()

	# pause video
	def pause(self):
		self.paused = True
		
	# play video
	def play(self):
		self.paused = False

	# set playback speed
	def setPlaybackSpeed(self, speed):
		self.speed = speed
		
	# force a frane update by defining "video_needs_frame_update=True"
	def forceUpdate(self):
		self.video_needs_frame_update=True

	# calc webcam/video fps
	def update_fps(self):
		fps_update_rate_sec = 1 # updates fps at every 1 sec
		time_delta = (time.time() - self.start_time)

		if time_delta >= fps_update_rate_sec:
			self.fps = self.frameCounter / fps_update_rate_sec
			self.frameCounter = 0
			self.start_time = time.time()		

	# QThread run
	def run(self):
		self.ThreadActive = True
		self.start_time = time.time()
		
		if self.source_file!=-1:

			# force video file capture to be first backend available
			if self.source_type=='video': self.capture_api = cv2.CAP_ANY

			# openCv capture
			capture = cv2.VideoCapture(self.source_file, self.capture_api)
			capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

			# get/set webcam properties
			if self.source_type=='webcam':
				self.video_needs_frame_update = True
				if self.resolution is not None:
					capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
					capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

			# get/set video properties
			if self.source_type=='video':
				_, tmp_frame = capture.read()
				self.source_fps = capture.get(cv2.CAP_PROP_FPS)
				self.resolution = [tmp_frame.shape[1], tmp_frame.shape[0]]
				self.num_frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)-1

			if capture.isOpened(): 
				self.stopped = False
				self.capture_api_name = cv2.videoio_registry.getBackendName(int(capture.get(cv2.CAP_PROP_BACKEND)))

				# main loop
				while self.ThreadActive:

					# if video, check if it should update the current frame
					if self.source_type=='video': self.CalcUpdateVideoFrame()
					
					# if frame update is needed (webcam always need an update!)
					if self.video_needs_frame_update:

						self.frameCounter += 1

						# if video, manually set current capture frame
						if self.source_type=='video': 
							capture.set(cv2.CAP_PROP_POS_FRAMES, int(self.frame))
							
						# read image
						ret, self.cvframe = capture.read()
						if ret:

							# should flip image?
							if self.flipImage: self.cvframe = cv2.flip(self.cvframe, 1)

							# convert BGR->RGB 
							self.imageBGR = self.cvframe
							self.imageRGB = cv2.cvtColor(self.cvframe, cv2.COLOR_BGR2RGB)
							
							# convert to QImage and emit update signal
							# imageDISPLAY can be set from outside to annotate images, otherwise use raw cv frame
							if self.imageDISPLAY is not None:
								self.imageQT = self.convertToQtImage(self.imageDISPLAY)
							else:
								self.imageQT = self.convertToQtImage(self.imageRGB)

							# emit ImageUpdate QT signal
							if self.ThreadActive: self.ImageUpdate.emit(self.imageQT)

						# if video, reset last_frame_update_time and video_needs_frame_update
						if self.source_type=='video': 
							self.pos_msec = capture.get(cv2.CAP_PROP_POS_MSEC)
							self.last_frame_update_time = time.time()
							self.video_needs_frame_update = False

					# update playback fps
					self.update_fps()

			capture.release()
			self.num_frames = -1
			self.stopped = True			

	# QThread stop
	def stop(self):
		self.ThreadActive = False
		self.quit()

	# converts openCV RGB image into q QtImage
	def convertToQtImage(self, image):
		return QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888)

	# if reading from a video file, this will check time to see if current frame needs an update (to match source file fps)
	def CalcUpdateVideoFrame(self):
		if not self.paused:
			elapsed_time = time.time()-self.last_frame_update_time
			update_rate = 1.0/float(self.source_fps)/self.speed
			if elapsed_time>=update_rate:
				self.frame += 1
				self.frame = self.frame%(self.num_frames-1)  # loop
				self.video_needs_frame_update = True
				self.last_update_time = time.time()
