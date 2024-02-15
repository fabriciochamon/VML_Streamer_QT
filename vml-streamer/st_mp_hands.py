import platform, cv2, resources, time, socket, json
import mediapipe as mp
import numpy as np
from one_euro_filter import OneEuroFilter
from mediapipe.framework.formats import landmark_pb2
from mediapipe import solutions
from mediapipe.tasks import python as tasks
from mediapipe.tasks.python import vision

class MediaPipeHands:

	def __init__(self):
		self.label = 'MediaPipe - Hands'
		self.description = 'Sends hand trackers from MediaPipe'
		self.settings = [
			{
				'name': 'motion_filter',
				'label': 'Motion Filter',
				'description':  'Applies as "One-Euro" filter over the input signal. '\
								'One-Euro is ideal for realtime data, since its fast '\
								'and only requires two time samples (current and previous frame).',
				'type': bool,
				'default_value': True,
			},
			{
				'name': 'smooth_factor',
				'label': 'Smooth Factor',
				'description': 'The amount of motion "smoothness" added by the One-Euro filter.',
				'type': float,
				'default_value': 60,
				'min_value': 0,
				'max_value': 100,
			},	
			{
				'name': 'draw',
				'label': 'Draw skeleton',
				'description': 'Annotate the UI display image with hand skeletons.',
				'type': bool,
				'default_value': True,
			},		
		]
		
		self.init = False	

	def run(self, video, stream, streams):

		self.video = video
		settings = stream['settings']

		# All mediapipe detections run asynchronously, 
		# for this reason we always return None and 
		# take control of when to send the data 
		# through the socket connection

		# socket info
		self.addr_port = (stream['address'], stream['port'])
		
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
		self.one_euro_beta = self.change_range(settings['smooth_factor'], 0, 100, 300, 2)
		
		'''
		Init MP data on first run.

		MediaPipe can take some seconds to intialize, so it is preferrable to init once inside run() instead of __init__()
		This way it doesn't slow down the interface when creating the combo boxes.
		'''
		if not self.init:
			self.iteration = 0
			self.joints = {}
			self.filtered_vals = {}
			self.mp_data_filter = {}
			self.running_mode = vision.RunningMode.LIVE_STREAM
			self.delegate = tasks.BaseOptions.Delegate.GPU if platform.system()=='Linux' else tasks.BaseOptions.Delegate.CPU

			self.base_options = tasks.BaseOptions(
				model_asset_path=resources.getPath('models/mp_hand.task'), 
				delegate=self.delegate
			)

			self.options = vision.HandLandmarkerOptions(
				base_options=self.base_options, 
				min_hand_detection_confidence=0.8, 
				min_tracking_confidence=0.5, 
				num_hands=2, 
				running_mode=self.running_mode, 
				result_callback=self.on_detection
			)

			self.detector = vision.HandLandmarker.create_from_options(self.options)	

			# since we want async detection, run() will return None and we implement our own socket process
			self.skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

			self.init = True

		# detect asynchronously
		try: 
			self.detector.detect_async(image=self.image, timestamp_ms=int(time.time()*1000))
		except: 
			# avoid raising errors for "Input timestamp must be monotonically increasing."
			pass

		return None

	def on_detection(self, result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
		self.iteration += 1
		self.joints = {}

		# should annotate image?
		image_annotated = None
		if self.annotate:
			image_annotated = self.video.imageBGR.copy()
			image_annotated = cv2.flip(image_annotated, 1)
		else:
			self.video.imageDISPLAY = None

		# loop through found hands
		for i, hand_landmarks in enumerate(result.hand_landmarks):

			# get landmarks
			hand_world_landmarks = result.hand_world_landmarks[i]
			handedness = result.handedness[i]
			
			###################################################################################################
			# convert to proper 3d world coordinates
			# thanks to Fryderyk Kogl
			# for providing the code: https://github.com/google/mediapipe/issues/2199#issuecomment-1172971018
			###################################################################################################
			model_points = np.float32([[-l.x, -l.y, -l.z] for l in hand_world_landmarks])
			image_points = np.float32([[l.x * self.frame_width, l.y * self.frame_height] for l in hand_landmarks])
			success, rotation_vector, translation_vector = cv2.solvePnP(model_points, image_points, self.camera_matrix, self.distortion, flags=cv2.SOLVEPNP_SQPNP)
			transformation = np.eye(4)
			transformation[0:3, 3] = translation_vector.squeeze()
			model_points_hom = np.concatenate((model_points, np.ones((21, 1))), axis=1)
			world_points = model_points_hom.dot(np.linalg.inv(transformation).T)

			# draw landmarks over cv image
			if self.annotate:
				hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
				hand_landmarks_proto.landmark.extend([ landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in hand_landmarks ])
				solutions.drawing_utils.draw_landmarks(
					image_annotated,
					hand_landmarks_proto,
					solutions.hands.HAND_CONNECTIONS,
					solutions.drawing_styles.get_default_hand_landmarks_style(),
					solutions.drawing_styles.get_default_hand_connections_style()
					)				
			
			# populate hand dict
			hand_name = handedness[0].category_name
			self.joints[hand_name] = []

			# loop through landmarks
			for lm_idx, lm in enumerate(world_points):
				
				# apply one-euro-filter to smooth signal for each landmark axis
				for axis in range(3):
					self.filtered_vals[f'{hand_name}{lm_idx}{axis}'] = lm[axis]	

					if self.apply_filter:
						if f'{hand_name}{lm_idx}{axis}' not in self.mp_data_filter.keys():
							self.mp_data_filter[f'{hand_name}{lm_idx}{axis}'] = OneEuroFilter(self.iteration, lm[axis], min_cutoff=self.one_euro_min_cutoff, beta=self.one_euro_beta)
							self.filtered_vals[f'{hand_name}{lm_idx}{axis}'] = lm[axis]							
						else:
							try:
								self.mp_data_filter[f'{hand_name}{lm_idx}{axis}'].beta = self.one_euro_beta
								self.filtered_vals[f'{hand_name}{lm_idx}{axis}'] = self.mp_data_filter[f'{hand_name}{lm_idx}{axis}'](self.iteration, lm[axis])
								if np.isnan(self.filtered_vals[f'{hand_name}{lm_idx}{axis}']):
									self.mp_data_filter[f'{hand_name}{lm_idx}{axis}'] = OneEuroFilter(self.iteration, lm[axis], min_cutoff=self.one_euro_min_cutoff, beta=self.one_euro_beta)
									self.filtered_vals[f'{hand_name}{lm_idx}{axis}'] = lm[axis]	
							except:
								self.filtered_vals[f'{hand_name}{lm_idx}{axis}'] = lm[axis]	

				# set joints dict
				self.joints[hand_name].append(
					{
						'x':self.filtered_vals[f'{hand_name}{lm_idx}0'],
						'y':self.filtered_vals[f'{hand_name}{lm_idx}1'],
						'z':self.filtered_vals[f'{hand_name}{lm_idx}2'],
					}
				)

		
		# send data through socket
		self.skt.sendto(json.dumps(self.joints).encode(), self.addr_port)

		# update video feedback with annotated image
		if self.annotate:
			image_annotated = cv2.flip(image_annotated, 1) 
			image_annotated = cv2.cvtColor(image_annotated, cv2.COLOR_BGR2RGB)
			self.video.imageDISPLAY = image_annotated		
		
	# helper function to remap value
	def change_range(self, unscaled, from_min, from_max, to_min, to_max):
		return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min