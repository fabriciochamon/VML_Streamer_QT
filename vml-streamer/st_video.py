import cv2

class Video:

	def __init__(self):
		self.label = 'Video'
		self.description = 'Sends the incoming video frame'
		self.return_type = 'numpy array'
		self.settings = [
			{
				'name': 'res_mult',
				'label': 'Resolution Multiplier',
				'type': float,
				'value': 1,
				'min_value': 0,
				'max_value': 1,
			}
		]

	def run(self, video, stream, streams):
		settings = stream['settings']
		image = video.imageBGR.copy()

		# resize?
		if settings['res_mult'] < 1:
			resize_dimensions = (int(video.imageBGR.shape[1]*settings['res_mult']), int(video.imageBGR.shape[0]*settings['res_mult']))
			image = cv2.resize(image, resize_dimensions, interpolation=cv2.INTER_LINEAR) 
		
		image_as_jpg = cv2.imencode('.jpg', image, params=[cv2.IMWRITE_JPEG_QUALITY, 85])[1]
		
		return image_as_jpg