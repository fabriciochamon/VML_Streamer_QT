# ---------------------------------------------------------------------------- #
# RENAME THIS FILE TO 'st_stream_template.py' TO MAKE IT AVAILABLE IN THE UI ! #
# ---------------------------------------------------------------------------- #

'''
This is a template for a new stream type. 
In this example we will stream the video resolution multiplied by a custom value, along with some extra info.
Stream types are defined as classes living inside their own python files. 
The python file must start with "st_" for VML Streamer to pick up the new stream type.
'''

class ExampleStream:
	'''
	The class needs at least 2 methods:
	  > __init__() constructor where you define stream properties, like label, description and config settings.
	  >   run()    where you return the data that is sent from VML Streamer. Return types available are:
	  			     - dict: sent as a dumped json string
	  	           	 - numpy array: sent as a video frame (flattened list of uint8: 0-255 rgb values)
   	 
   	 And offers an optional method:
   	  > terminate() fired when user deletes the stream instance from the UI (use it cleanup resources, close connections, etc.)
	'''
	def __init__(self):
		
		# label shown in the combo box
		self.label = 'Example Stream'  

		# description shown as a tooltip when user hovers the item inside the combo box (accepts html tags)
		self.description =  'Sends a dict with video resolution and some extra info'

		# (optional, when absent defaults to True)
		# if needs_video_input == False, VML Streamer won't wait for an available video source to start streaming the data. 
		self.needs_video_input = True

		# (optional. when absent, defaults to '')
		# The returned data type from this stream. Shown in the tooltip and helps informing the user on how to decode data coming from this stream.
		self.return_type = 'dict'		

		'''
		Below we define optional extra config settings for our new stream type. This should be a list of dicts (more info below).

		At the moment the supported types are:
			- bool  (shown as a checkbox)
			- float (shown as a slider)
			- int   (shown as a input text field)
			- str   (shown as an input text field. Or a rich text (html) field, see below!)
			- list  (shown as a combo box)

		A field dict is formatted as follows:
			
			REQUIRED keys: 
				"name"  (unique, should not contain spaces!)
				"label" (UI display name, can contain spaces and special chars)
				"type"  (bool | float | int | str | list)
			
			OPTIONAL keys:
				"default_value" (field initial value)
				"min_value" (available for float fields only. This is the min value of the slider)
				"max_value" (available for float fields only. This is the max value of the slider)
				"description" (extended info shown as a tooltip when user hovers the field label)
				"ui_type" 
					- 'html': renders a html field instead of the regular textinput field (for "str")
					- 'textinput': renders a textinput field instead of the regular slider field (for "float")

		'''
		self.settings = [

			# a checkbox
			{
				'name': 'do_mult_resolution',
				'label': 'Multiply resolution',
				'description': 'When checked, the resolution will be multiplied.',
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
				'description': 'The chosen item will be sent along with the stream.',
				'type': list,
				'default_value': ['Item A', 'Item B', 'Item C'],  # it can also accept a list of dicts, where key=label and value=value
			},

			# an info box
			{
				'name': 'info',
				'label': 'Info',
				'description': 'Some additional help for the user',
				'type': str,
				'ui_type': 'html',  # <-- a read-only, html enabled, multiline field.
				'default_value': """
					This info box accepts any kind of <b>html</b> tags. <br><br>Including links: <a href="http://www.sidefx.com">SideFX Houdini</a>.
				""",
			},			
		]

	'''
	The "run()" method takes 3 args:
		- video (object): The object containing information about the current video frame being displayed. Things you can access:
						video.imageBGR = openCV frame (in BGR channel ordering)
						video.imageRGB = openCV frame (in RGB channel ordering). 
						video.imageDISPLAY = image to be displayed in the UI (in RGB channel ordering), you can override this value to annotate images. 
						video.source_type = 'webcam' or 'video'
						video.source_file = if reading from a webcam it will be the device id (0, for example). If reading from a video file it will be the file path.
						video.resolution = video resolution in the format [res_X, res_Y]
						video.frame = if reading from a video file, this is the current frame number being displayed (always starts at 1!)
						video.num_frames = if reading from a video file, this is the actual length of the video in number of frames
						video.fps = current video/webcam framerate
						video.source_fps = video file original framerate
						video.flipImage = if video flipped?
						video.stopped = is video stopped?
						video.paused = is video paused?
						video.capture_api = openCV video capture backend (as int)
						video.capture_api_name = openCV video capture backend (as string)

		- stream (dict): The current stream instance being processed. Things you can access:
						stream['address'] = the IP address to where the data is being sent to
						stream['port'] = the port to where the data is being sent to
						stream['settings'] = the actual values of UI fields defined in the __init__() constructor (keys = field names)
											 Example: stream['settings']['my_field_name']

		- streams (list): A list of all stream instances being processed (including self). You can use this list to access data from other streams if needed. 
						  Example: streams[index]['data']  (order of operation follows the UI, you can only access current data from previous streams)
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

	# (optional)
	# close connections, cleanup resources, etc
	def terminate(self):
		pass
