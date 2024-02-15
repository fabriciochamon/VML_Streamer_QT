import platform, cv2, resources, time, socket, json
import mediapipe as mp
import numpy as np
from one_euro_filter import OneEuroFilter
from mediapipe.framework.formats import landmark_pb2
from mediapipe import solutions
from mediapipe.tasks import python as tasks
from mediapipe.tasks.python import vision

class MediaPipeFace:

	def __init__(self):
		self.label = 'MediaPipe - Face'
		self.description = 'Sends face trackers from MediaPipe'
		self.settings = [
			{
				'name': 'draw',
				'label': 'Draw mask',
				'description': 'Annotate the UI display image with a face mask wireframe.',
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
		
		# input image to MP format (track flipped image as it feels better in the 3d viewport)
		image = cv2.flip(video.imageBGR, 1) 
		image = cv2.imencode('.jpg', image, params=[cv2.IMWRITE_JPEG_QUALITY, 85])[1]
		image = cv2.imdecode(image, cv2.IMREAD_COLOR)
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
		self.image = mp.Image(mp.ImageFormat.SRGB, data=image)
		
		'''
		Init MP data on first run.

		MediaPipe can take some seconds to intialize, so it is preferrable to init once inside run() instead of __init__()
		This way it doesn't slow down the interface when creating the combo boxes.
		'''
		if not self.init:
			self.joints = {}
			self.running_mode = vision.RunningMode.LIVE_STREAM
			self.delegate = tasks.BaseOptions.Delegate.GPU if platform.system()=='Linux' else tasks.BaseOptions.Delegate.CPU

			self.base_options = tasks.BaseOptions(
				model_asset_path=resources.getPath('models/mp_face.task'), 
				delegate=self.delegate
			)

			self.options = vision.FaceLandmarkerOptions(
				base_options=self.base_options, 
				output_facial_transformation_matrixes=True, 
				min_face_detection_confidence=0.8, 
				min_tracking_confidence=0.5, 
				num_faces=1, 
				running_mode=self.running_mode, 
				result_callback=self.on_detection
			)

			self.detector = vision.FaceLandmarker.create_from_options(self.options)	

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

	def on_detection(self, result: vision.FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
		self.joints = {}

		# should annotate image?
		image_annotated = None
		if self.annotate:
			image_annotated = self.video.imageBGR.copy()
			image_annotated = cv2.flip(image_annotated, 1)
		else:
			self.video.imageDISPLAY = None

		# loop through found faces
		for i, face_landmarks in enumerate(result.face_landmarks):

			# draw landmarks over cv image
			if self.annotate:
				face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
				face_landmarks_proto.landmark.extend([ landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in face_landmarks ])
				solutions.drawing_utils.draw_landmarks(
						image_annotated,
						face_landmarks_proto,
						solutions.face_mesh.FACEMESH_TESSELATION,
						None,
						solutions.drawing_styles.get_default_face_mesh_tesselation_style()
					)
				solutions.drawing_utils.draw_landmarks(
						image_annotated,
						face_landmarks_proto,
						solutions.face_mesh.FACEMESH_CONTOURS,
						None,
						solutions.drawing_styles.get_default_face_mesh_contours_style()
					)
				solutions.drawing_utils.draw_landmarks(
						image_annotated,
						face_landmarks_proto,
						solutions.face_mesh.FACEMESH_IRISES,
						None,
						solutions.drawing_styles.get_default_face_mesh_iris_connections_style()
					)		
			
			# populate joints
			face_name = f'Face{i}'
			self.joints[face_name] = []

			for lm in face_landmarks:
				self.joints[face_name].append(
						{
							'x':lm.x,
							'y':lm.y,
							'z':lm.z,
						}
					)

			# populate xform
			face_xform = result.facial_transformation_matrixes[i]
			face_xform = [j for sub in face_xform for j in sub]
			self.joints[face_name+'_xform'] = face_xform
			aspect = 1+(((self.video.resolution[0]/self.video.resolution[1])-1)/2)
			self.joints[face_name+'_aspect'] = aspect
		
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