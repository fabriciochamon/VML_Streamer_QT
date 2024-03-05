import websocket, socket, copy, json, time
from websocket import create_connection

class AndroidSensors:
	def __init__(self):	
		self.label = 'Android Sensors'  
		self.description =  'Sends sensor data from android devices'
		self.needs_video_input = False
		self.return_type = 'dict'
		host_ip = '.'.join(socket.gethostbyname(socket.gethostname()).split('.')[0:3])+'.x'

		self.sensors = [
			'android.sensor.proximity',
			'android.sensor.magnetic_field',
			'android.sensor.magnetic_field_uncalibrated',
			'android.sensor.gyroscope',
			'android.sensor.gyroscope_uncalibrated',
			'android.sensor.rotation_vector',
			'android.sensor.game_rotation_vector',
			'android.sensor.gravity',
			'android.sensor.linear_acceleration',
			'android.sensor.step_counter',
			'android.sensor.device_orientation',
			'android.sensor.accelerometer',
			'android.sensor.accelerometer_uncalibrated',
			'android.sensor.light',
		]

		self.settings = [
			{
				'name': 'sensorServerIp',
				'label': 'Sensor Server IP',
				'description': 'Your android device IP address.',
				'type': str,
				'default_value': host_ip,
			},
			{
				'name': 'sensorServerPort',
				'label': 'Sensor Server Port',
				'type': str,
				'default_value': '8080',
			},
			{
				'name': 'info',
				'label': 'Info',
				'type': str,
				'ui_type': 'html',
				'default_value': """
					Receives <a href="https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview">sensor data</a> from <a href="https://github.com/umer0586/SensorServer">SensorServer</a>.<br><br>

					<small><font color=grey>Manually install the .apk to your android device.<br><br>
					*tip: lower the sensor sampling rate in the app to get better response times</font></small>
				"""
			}	
		]

		self.ws_connected = False
		self.currSettings = None
		self.prevSettings = None
		self.last_values = {}
		self.ws = None

		# add socket for streaming
		self.skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

	def on_message(self, ws, message):
		msg = json.loads(message)
		data = {}
		for sensor in self.sensors:
			values = self.last_values[sensor] if (self.last_values is not None and sensor in self.last_values.keys()) else []
			data[sensor] = msg['values'] if msg['type']==sensor else values
			self.last_values[sensor] = data[sensor]

		if self.skt is not None: 
			for addr_port in self.addr_ports:
				self.skt.sendto(json.dumps(data).encode(), addr_port)
	
	def on_error(self, ws, error):
		print(f'Android sensors: websocket error. ({error})')
		self.disconnect()
		
	def on_close(self, ws, close_code, reason):
		print(f'Android sensors: websocket connection closed. (reason: {reason})')
		self.disconnect()
		
	def on_open(self, ws):
		print(f'Android sensors: websocket connected.')

	def connect(self, url):
		self.ws_connected = True
		self.ws = websocket.WebSocketApp(
				url,
				on_open=self.on_open,
				on_message=self.on_message,
				on_error=self.on_error,
				on_close=self.on_close,
			)

		self.ws.run_forever()

	def disconnect(self):
		if self.ws is not None: self.ws.close()
		self.ws_connected=False
		self.ws = None
		self.last_sensor_type = None
		
	def run(self, video, stream, streams):
		
		# store settings
		self.instance_settings = stream['settings']
		
		# ip address field should also accepts a comma delimited list, so we handle that
		self.addr_ports = [(addr.strip(), stream['port']) for addr in stream['address'].split(',')]

		# check if needs websocket restart
		self.currSettings = copy.deepcopy(self.instance_settings)
		if self.currSettings != self.prevSettings:
			self.disconnect()
			self.prevSettings = copy.deepcopy(self.currSettings)

		# connect to websocket
		if not self.ws_connected:	
			all_sensors_str = str(self.sensors).replace("\'", "\"").replace(', ', ',')
			endpoint = f'/sensors/connect?types={all_sensors_str}'
			conn_url = f'ws://{self.instance_settings["sensorServerIp"]}:{self.instance_settings["sensorServerPort"]}{endpoint}'
			self.connect(conn_url) 
			
		return None

	def terminate(self):
		self.disconnect()
		self.ws = None
		self.currSettings = None
		self.prevSettings = None


