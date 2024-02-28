class InfoDict:

	def __init__(self):
		self.label = 'Info Dictionary'
		self.description = 'Sends a python dict with information about the input video source.'
		
	def run(self, video, stream, streams):
		info = {}
		info['image_width']  = int(video.resolution[0])
		info['image_height'] = int(video.resolution[1])
		info['source_type']  = video.source_type
		info['source_file']  = video.source_file
		info['flip_image']  = video.flipImage
		if video.source_type=='video':
			info['num_frames']  = video.num_frames
			info['curr_frame']  = video.frame
			info['source_fps']  = video.source_fps
		info['streams'] = [
				{
					'type':    st['type'],
					'address': st['address'],
					'port':    st['port'],
				}
				for st in streams
			]
		return info