# ---------------------------------------------------------------------------- #
# RENAME THIS FILE TO 'st_stream_template.py' TO MAKE IT AVAILABLE IN THE UI ! #
# ---------------------------------------------------------------------------- #

'''
This is a simple template for a new stream type. 
In this example we will stream the video resolution, multiplied by a custom value, and along with some custom text and a custom item choice from a list.

Stream types are defined as simple classes, living inside their own python files. 
The python file must start with "st_", so when VML Streamer starts it will parse the file attributes, 
and make the new stream type available in the UI.
'''

class MyCustomStream:
	'''
	The class needs at least 2 methods:
	  > __init__() where you define stream properties, like label, description and config settings.
	  >   run()    where you return data to be sent through sockets. Return types available:
	  			     - dict: sent as a dumped json string
	  	           	 - numpy array: sent as a video frame (flattened list of uint8: 0-255 rgb values)
	'''
	def __init__(self):
		
		# define the stream type name shown at the combo box
		self.label = 'Image Resolution'  

		# define the stream type description shown as a tooltip (when user hovers the item inside the combo box)
		self.description =  'Sends a python dict with the video resolution '\
							'(optionally multiplied by a float value), along with some custom text.'

		'''
		Below we define optional extra config settings for our new stream type. This should be a list of dicts (more info below).

		At the moment the only supported UI types are:
			- bool  (shown as a checkbox)
			- float (shown as a slider)
			- str   (shown as an input text field)
			- list  (shown as a combo box)

		A field dict is formatted as follows:
			
			REQUIRED keys: 
				"name"  (should not contain spaces!)
				"label" (UI display name, can contain spaces and special chars)
				"type"  (bool | float | str)
			
			OPTIONAL keys:
				"default_value" (field initial value)
				"min_value" (available for float fields only. This is the min value of the slider)
				"max_value" (available for float fields only. This is the max value of the slider)
				"description" (extended info shown as a tooltip when user hovers the field label)

		'''
		self.settings = [

			# a checkbox
			{
				'name': 'do_mult_resolution',
				'label': 'Multiply resolution',
				'description': 'When checked, the resolution will be multiplied by the "Value" field below.',
				'type': bool,
				'default_value': True,
			},

			# a slider
			{
				'name': 'mult_resolution_value',
				'label': 'Value',
				'description': 'Multiplication factor for resolution.',
				'type': float,
				'default_value': 3,
				'min_value': 0,
				'max_value': 10,
			},

			# a text field
			{
				'name': 'extra_text',
				'label': 'Extra text',
				'description': 'Some custom text that is sent together with the resolution.',
				'type': str,
				'default_value': 'This is a custom string.',
			},

			# a combo box field
			{
				'name': 'choices',
				'label': 'Choices',
				'description': 'Choose an item from the list',
				'type': list,
				'default_value': ['Item A', 'Item B', 'Item C'],  # it can also accept a list of dicts, where key=label and value=value
			},
		]

	'''
	The run() method takes 3 args:
		- (object) video: The video object containing information about the current frame being displayed in the UI. Things you can access:
						video.imageBGR = openCV frame (in BGR channel ordering)
						video.imageRGB = openCV frame (in RGB channel ordering). 
						video.imageDISPLAY = image to be displayed in the UI (in RGB channel ordering), you can override this value to annotate images. 
											 (Make sure to match the np.array shape from video.imageRGB)
						video.source_type = 'webcam' or 'video'
						video.source_file = if reading from a webcam it will be the device id (0, for example). If reading from a video file it will be the file path.
						video.resolution = video resolution in the format [res_X, res_Y]
						video.frame = if reading from a video file this is the current frame number being displayed (always starts at 1!)
						video.num_frames = if reading from a video file this is the actual length of the video (total number of frames)
						video.fps = current video/webcam framerate
						video.source_fps = video file original framerate
						video.flipImage = if video flipped?
						video.stopped = is video stopped?
						video.paused = is video paused?
						video.capture_api = openCV video capture backend (as int)
						video.capture_api_name = openCV video capture backend (as string)

		- (dict) stream: The current stream instance being processed. Things you can access:
						stream['address'] = the IP address to where the data is being sent to
						stream['port'] = the port to where the data is being sent to
						stream['settings'] = the actual values of UI fields defined above in the __init__() constructor (keys = field "name")
											 Example: stream['settings']['my_field_name']

		- (list) streams: A list of all stream instances being processed (including self!). You can use this list to access other streams if needed. 
						  An example use case is accessing data from a previous stream "run()" result into the current stream, like: streams[index]['data']
	'''
	def run(self, video, stream, streams):

		settings = stream['settings']
		
		data = {
			'res_X': video.resolution[0],
			'res_Y': video.resolution[1],
			'text':  settings['extra_text'],
			'chosen_item': settings['choice'],
		}

		if settings['do_mult_resolution']:
			data['res_X'] *= settings['mult_resolution_value']
			data['res_Y'] *= settings['mult_resolution_value']

		return data
