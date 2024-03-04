import socket, time, json, numpy as np
from PySide6 import QtCore

class StreamThread(QtCore.QThread):
	def __init__(self, streams=[], processors=[], VideoThread=None):
		super().__init__()
		self.streams = streams
		self.processors = processors
		self.VideoThread = VideoThread

		# Init UDP socket connection
		self.skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

	# QThread run
	def run(self):
		self.ThreadActive = True
		while self.ThreadActive: 

			# loop through streams, filter by non-video based streams
			filtered_streams = [x for x in self.streams if not x['needs_video_input']]
			for stream in filtered_streams:
				idx = self.streams.index(stream)
				data = self.processors[stream['type']].run(self.VideoThread, stream, self.streams)
				try:
					self.streams[idx]['data'] = data
				except:
					pass
				
				# send data through UDP socket
				if data is not None:
					addr_ports = [(x.strip(), stream['port']) for x in stream['address'].split(',')]

					for addr_port in addr_ports:
						
						# send dict
						if isinstance(data, dict):
							self.skt.sendto(json.dumps(data).encode(), addr_port)

						# send numpy array
						elif isinstance(data, np.ndarray):
							self.skt.sendto(data.tobytes(), addr_port)

			time.sleep(0.2)

	# QThread stop
	def stop(self):
		self.ThreadActive = False
		self.quit()