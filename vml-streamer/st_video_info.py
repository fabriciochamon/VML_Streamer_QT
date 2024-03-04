class InfoDict:

	def __init__(self):
		self.label = 'Video Info'
		self.description = 'Sends information about the input video source'
		self.return_type = 'dict'
		
	def run(self, video, stream, streams):
		info = {}
		info['image_width']  = int(video.resolution[0])
		info['image_height'] = int(video.resolution[1])
		info['source_type']  = video.source_type
		info['source_file']  = video.source_file
		info['flip_image']  = video.flipImage
		
		# if a video stream is present, multiply image resolution by its multiplier field:
		has_video_stream = len([s for s in streams if s['type']=='Video'])
		if has_video_stream:
			res_mult = [s['settings']['res_mult'] for s in streams if s['type']=='Video'][0]
			info['image_width']  = int(info['image_width']*res_mult)
			info['image_height'] = int(info['image_height']*res_mult)

		# if playing a video file, add extra info
		if video.source_type=='video':
			info['num_frames']  = video.num_frames
			info['curr_frame']  = video.frame
			info['source_fps']  = video.source_fps

		# populate streams list
		info['streams'] = [
				{
					'type':    st['type'],
					'address': st['address'],
					'port':    st['port'],
				}
				for st in streams
			]

		return info