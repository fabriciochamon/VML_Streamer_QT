import platform, cv2, resources, time, socket, json
import mediapipe as mp
import numpy as np
from one_euro_filter import OneEuroFilter
from mediapipe.framework.formats import landmark_pb2
from mediapipe import solutions
from mediapipe.tasks import python as tasks
from mediapipe.tasks.python import vision

class MediaPipeBody:

	def __init__(self):
		self.label = 'MediaPipe - Body'
		self.description = 'Sends body trackers from MediaPipe'
		self.return_type = 'dict'
		self.settings = [
			{
				'name': 'num_bodies',
				'label': 'Num Bodies',
				'description': 'MediaPipe will try to detect up to this number of bodies in the input video',
				'type': int,
				'default_value': 1,
			},
			{
				'name': '3d_coords',
				'label': '3D Coordinates',
				'description': 'Tries to estimate full 3d coordinates from MediaPipe (can potentially introduce Z-depth jitter to trackers).<br><br>When unchecked will output hips fixed at the origin.',
				'type': bool,
				'default_value': True,
			},
			{
				'name': 'min_body_presence_confidence',
				'label': 'Min body presence confidence',
				'description': 'The minimum confidence score of body presence. (Range: 0-1)<br><br>'\
								'<small><font color=grey>MediaPipe detections runs a 2-step process to identify pose landmarks: <br>'\
								'First it detects if one or more bodies are present in the frame, only then it will proceed to the body landmarks detection.</font></small>',
				'type': float,
				'default_value': 0.8,
				'ui_type': 'textinput',
			},	
			{
				'name': 'min_tracking_confidence',
				'label': 'Min tracking confidence',
				'description': 'The minimum confidence score for the pose tracking to be considered successful. (Range: 0-1)',
				'type': float,
				'default_value': 0.5,
				'ui_type': 'textinput',
			},	
			{
				'name': 'motion_filter',
				'label': 'Motion Filter',
				'description':  'Applies as "One-Euro" filter over the input signal. <br><br>'\
								'<small><font color=grey>One-Euro is ideal for realtime data, since its fast '\
								'and only requires two time samples (current and previous frame).</font></small>',
				'type': bool,
				'default_value': True,
			},
			{
				'name': 'smooth_factor',
				'label': 'Smooth Factor',
				'description': 'The amount of motion "smoothness" added by the One-Euro filter.',
				'type': float,
				'default_value': 90,
				'min_value': 0,
				'max_value': 100,
			},	
			{
				'name': 'draw',
				'label': 'Draw skeleton',
				'description': 'Annotate the UI display image with a body skeleton.',
				'type': bool,
				'default_value': True,
			},		
		]
		
		self.init = False	
		self.last_settings = None
		self.pause_detection = False

	def run(self, video, stream, streams):

		self.video = video
		settings = stream['settings']
		self.settings = settings

		# ip address field should also accepts a comma delimited list, so we handle that
		self.addr_ports = [(addr.strip(), stream['port']) for addr in stream['address'].split(',')]
		
		# should annotate image ?
		self.annotate = settings['draw']
		
		# resolution
		self.frame_width = video.resolution[0]
		self.frame_height = video.resolution[1]
		
		# input image to MP format (track flipped image as it feels better in the 3d viewport)
		image = cv2.flip(video.imageBGR, 1) 
		image = cv2.imencode('.jpg', image, params=[cv2.IMWRITE_JPEG_QUALITY, 85])[1]
		image = cv2.imdecode(image, cv2.IMREAD_COLOR)
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
		self.image = mp.Image(mp.ImageFormat.SRGB, data=image)
		
		# camera settings for 3d projection
		self.focal_length = self.frame_width * 0.75
		self.distortion = np.zeros((4, 1))
		self.center = (self.frame_width/2, self.frame_height/2)
		self.camera_matrix = np.array(
							 [[self.focal_length, 0, self.center[0]],
							 [0, self.focal_length, self.center[1]],
							 [0, 0, 1]], dtype = 'double'
							 )

		# one euro filter settings
		self.apply_filter = settings['motion_filter']
		self.one_euro_min_cutoff = 0.004
		self.one_euro_beta = self.change_range(settings['smooth_factor'], 0, 100, 200, 1)

		'''
		Init MP data on first run.

		MediaPipe can take some seconds to intialize, so it is preferrable to init once inside run() instead of __init__()
		This way it doesn't slow down the interface when creating the combo boxes.
		'''
		self.check_reinit()
		if not self.init:
			self.iteration = 0
			self.joints = {}
			self.filtered_vals = {}
			self.mp_data_filter = {}
			self.last_settings = settings.copy()
			self.running_mode = vision.RunningMode.LIVE_STREAM
			self.delegate = tasks.BaseOptions.Delegate.GPU if platform.system()=='Linux' else tasks.BaseOptions.Delegate.CPU

			self.base_options = tasks.BaseOptions(
				model_asset_path=resources.getPath('models/mp_body.task'), 
				delegate=self.delegate
			)

			self.options = vision.PoseLandmarkerOptions(
				base_options=self.base_options, 
				min_pose_detection_confidence=settings['min_body_presence_confidence'], 
				min_tracking_confidence=settings['min_tracking_confidence'], 
				num_poses=settings['num_bodies'], 
				running_mode=self.running_mode, 
				result_callback=self.on_detection,
			)

			self.detector = vision.PoseLandmarker.create_from_options(self.options)	

			# since we want async detection, run() will return None and we implement our own socket process
			self.skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

			self.init = True
			self.pause_detection = False

		# detect asynchronously
		try: 
			self.detector.detect_async(image=self.image, timestamp_ms=int(time.time()*1000))
		except: 
			# avoid raising errors for "Input timestamp must be monotonically increasing."
			pass

		# All mediapipe detections run asynchronously, 
		# for this reason we always return None and 
		# take control of when to send the data 
		# through the socket connection

		return None

	def check_reinit(self, exclude_fields=['motion_filter', 'smooth_factor', 'draw']):
		restart = False
		if self.last_settings is None: 
			self.init = False 
			self.detector = None
			restart = True			
		else:
			for k,v in self.settings.items():
				if k not in exclude_fields:
					if v != self.last_settings[k]: 
						self.init = False
						self.detector = None
						restart = True
						break

		if restart: self.pause_detection = True

	def on_detection(self, result: vision.PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
		if not self.pause_detection:
			self.iteration += 1
			self.joints = {}

			# should annotate image?
			image_annotated = None
			if self.annotate:
				image_annotated = self.video.imageBGR.copy()
				image_annotated = cv2.flip(image_annotated, 1)
			else:
				self.video.imageDISPLAY = None

			# loop through found poses
			for i, pose_landmarks in enumerate(result.pose_landmarks):
				
				# get landmarks
				pose_world_landmarks = result.pose_world_landmarks[i]

				# 3d estimation?
				if self.settings['3d_coords']:
					###################################################################################################
					# convert to proper 3d world coordinates
					# thanks to Fryderyk Kogl
					# for providing the code: https://github.com/google/mediapipe/issues/2199#issuecomment-1172971018
					###################################################################################################
					model_points = np.float32([[-l.x, -l.y, -l.z] for l in pose_world_landmarks])
					image_points = np.float32([[l.x * self.frame_width, l.y * self.frame_height] for l in pose_landmarks])
					success, rotation_vector, translation_vector = cv2.solvePnP(model_points, image_points, self.camera_matrix, self.distortion, flags=cv2.SOLVEPNP_SQPNP)
					if success:
						transformation = np.eye(4)
						transformation[0:3, 3] = translation_vector.squeeze()
						model_points_hom = np.concatenate((model_points, np.ones((33, 1))), axis=1)
						world_points = model_points_hom.dot(np.linalg.inv(transformation).T)
						self.prev_world_points = world_points
					else:
						world_points = self.prev_world_points
				
				# draw landmarks over cv image
				if self.annotate:
					pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
					pose_landmarks_proto.landmark.extend([ landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in pose_landmarks ])
					solutions.drawing_utils.draw_landmarks(
						image_annotated,
						pose_landmarks_proto,
						solutions.pose.POSE_CONNECTIONS,
						solutions.drawing_styles.get_default_pose_landmarks_style(),
						)			
				
				# populate pose dict
				pose_name = f'Body{i}'
				self.joints[pose_name] = {}
				self.joints[pose_name]['mode'] = '3d' if self.settings['3d_coords'] else 'default'
				self.joints[pose_name]['trackers'] = []

				# loop through landmarks
				tracker_points = world_points if self.settings['3d_coords'] else pose_world_landmarks
				for lm_idx, lm in enumerate(tracker_points):

					# apply one-euro-filter to smooth signal for each landmark axis
					for axis in range(3):
						if self.settings['3d_coords']:
							v = lm[axis]
						else:
							if axis==0: v = lm.x
							if axis==1: v = lm.y
							if axis==2: v = lm.z

						self.filtered_vals[f'{pose_name}{lm_idx}{axis}'] = v	

						if self.apply_filter:
							if f'{pose_name}{lm_idx}{axis}' not in self.mp_data_filter.keys():
								self.mp_data_filter[f'{pose_name}{lm_idx}{axis}'] = OneEuroFilter(self.iteration, v, min_cutoff=self.one_euro_min_cutoff, beta=self.one_euro_beta)
								self.filtered_vals[f'{pose_name}{lm_idx}{axis}'] = v							
							else:
								try:
									self.mp_data_filter[f'{pose_name}{lm_idx}{axis}'].beta = self.one_euro_beta
									self.filtered_vals[f'{pose_name}{lm_idx}{axis}'] = self.mp_data_filter[f'{pose_name}{lm_idx}{axis}'](self.iteration, v)
									if np.isnan(self.filtered_vals[f'{pose_name}{lm_idx}{axis}']):
										self.mp_data_filter[f'{pose_name}{lm_idx}{axis}'] = OneEuroFilter(self.iteration, v, min_cutoff=self.one_euro_min_cutoff, beta=self.one_euro_beta)
										self.filtered_vals[f'{pose_name}{lm_idx}{axis}'] = v	
								except:
									self.filtered_vals[f'{pose_name}{lm_idx}{axis}'] = v

					# set joints dict
					self.joints[pose_name]['trackers'].append(
						{
							'x':self.filtered_vals[f'{pose_name}{lm_idx}0'],
							'y':self.filtered_vals[f'{pose_name}{lm_idx}1'],
							'z':self.filtered_vals[f'{pose_name}{lm_idx}2'],
						}
					)
						
			# send data through socket
			for addr_port in self.addr_ports:
				self.skt.sendto(json.dumps(self.joints).encode(), addr_port)

			# update video feedback with annotated image
			if self.annotate:
				image_annotated = cv2.flip(image_annotated, 1) 
				image_annotated = cv2.cvtColor(image_annotated, cv2.COLOR_BGR2RGB)
				self.video.imageDISPLAY = image_annotated		
		
	# helper function to remap value
	def change_range(self, unscaled, from_min, from_max, to_min, to_max):
		return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min	

	# terminate
	def terminate(self):
		self.video.imageDISPLAY = None