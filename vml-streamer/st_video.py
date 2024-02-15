import cv2

class Video:

	def __init__(self):
		self.label = 'Video'
		self.description = 'Sends the incoming video frame as a numpy array.'
		self.settings = []

	def run(self, video, stream, streams):
		image_as_jpg = cv2.imencode('.jpg', video.imageBGR, params=[cv2.IMWRITE_JPEG_QUALITY, 85])[1]
		return image_as_jpg