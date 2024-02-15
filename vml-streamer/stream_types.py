from PySide6 import QtCore, QtWidgets, QtGui
import os, resources, qt_utils
from inspect import isclass
import stream_types_import

processors = None

# Build a processor list based on all python source files starting with "st_"
def getProcessors():
	global processors
	if processors is None:
		st_dir = resources.getPath('.')
		st_files = sorted([item for item in os.listdir(st_dir) if item.startswith('st_')])
		processors_list = {}
		for st_file in st_files:
			st = __import__(st_file.replace('.py', ''))
			classes = [x for x in dir(st) if isclass(getattr(st, x))]
			class_ = getattr(st, classes[0])
			instance = class_()
			processors_list[instance.label] = instance
		processors = processors_list

	return processors

# Build a Qt layout for each available processor
def getQtWidget(stream=None, caller=None, inline=False):

	# main layout
	layout_main = QtWidgets.QVBoxLayout()
	stream_name = f'stream{stream["id"]}'
	layout_main.setObjectName(stream_name)
	layout_main.addSpacing(20)
	all_widgets = []
	
	# btn delete stream
	widgets = []
	btn_delete = QtWidgets.QPushButton('X')
	btn_delete.setProperty('class', 'button-remove-stream')
	stream_label = QtWidgets.QLabel('Stream:')
	stream_label.setProperty('class', 'stream_entry')
	widgets.extend([btn_delete, stream_label])
	qt_utils.addRow(layout_main, widgets)
	all_widgets.extend(widgets)

	# address/port
	widgets = []
	addr = QtWidgets.QLineEdit(stream['address'])
	addr.setProperty('class', 'stream_extra_settings')
	addr.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
	addr.textChanged.connect(lambda new_address: caller.ChangeStreamAddr(new_address, stream['id']))
	port = QtWidgets.QLineEdit(str(stream['port']))
	port.setProperty('class', 'stream_extra_settings')
	port.setMaximumWidth(60)
	port.textChanged.connect(lambda new_port: caller.ChangeStreamPort(int(new_port), stream['id']))
	widgets.extend([QtWidgets.QLabel('Address:'), addr, QtWidgets.QLabel('Port:'), port])
	qt_utils.addRow(layout_main, widgets, add_stretches=False)
	all_widgets.extend(widgets)

	# stream type:
	widgets = []
	combo_type = QtWidgets.QComboBox()
	combo_type.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
	combo_type.setObjectName(f'{stream_name}__comboType')
	combo_type.currentTextChanged.connect(lambda txt: caller.ChangeStreamType(stream['id'], layout_main, txt))
	widgets.extend([QtWidgets.QLabel('Type:'), combo_type])
	qt_utils.addRow(layout_main, widgets, add_stretches=False)
	all_widgets.extend(widgets)

	for i, (label, instance) in enumerate(getProcessors().items()):
		
		# combo item
		combo_type.addItem(label)
		if hasattr(instance, 'description'):
			combo_type.setItemData(i, instance.description, QtCore.Qt.ToolTipRole)
			combo_type.setToolTipDuration(5)

		# extra settings per type
		grp_settings = QtWidgets.QGroupBox('Settings:')
		grp_settings.setObjectName(f'{stream_name}__settings__{label}')
		all_widgets.extend([grp_settings])
		layout_settings = QtWidgets.QFormLayout()
		grp_settings.setLayout(layout_settings)
		if i!=0: grp_settings.hide()

		if hasattr(instance, 'settings'):
			for setting in instance.settings:
				wid = None
				setting_name = f'{stream_name}__setting__{setting["name"]}__{label}'
				
				wid_label = QtWidgets.QLabel(setting['label'])
				if 'description' in setting.keys():
					tooltip = QtWidgets.QToolTip()
					wid_label.setToolTip(setting['description'])
					
				# handle boolean type
				if setting['type'] == bool:
					wid = QtWidgets.QCheckBox()
					wid.stateChanged.connect(lambda new_value, setting=setting: caller.ChangeStreamSettings(stream['id'], setting['name'], new_value==2))
					if 'default_value' in setting.keys(): wid.setChecked(setting['default_value'])
					layout_settings.addRow(wid_label, wid)

				# handle float type
				elif setting['type'] == float:
					if 'default_value' in setting.keys(): default_value = setting['default_value']
					else: default_value = 1

					if 'min_value' in setting.keys():
						min_value = setting['min_value']
						max_value = setting['max_value']
					else:
						min_value = 0
						max_value = default_value*2

					wid = qt_utils.SliderWithNumbers(min_value, max_value, default_value)
					wid.slider.valueChanged.connect(lambda new_value, setting=setting: caller.ChangeStreamSettings(stream['id'], setting['name'], new_value/10))
					layout_settings.addRow(wid_label, wid)

				# handle string type
				elif setting['type'] == str:
					wid = QtWidgets.QLineEdit()
					wid.setProperty('class', 'stream_extra_settings')
					wid.textChanged.connect(lambda new_value, setting=setting: caller.ChangeStreamSettings(stream['id'], setting['name'], new_value))
					if 'default_value' in setting.keys(): wid.setText(setting['default_value'])
					layout_settings.addRow(wid_label, wid)

				wid.setObjectName(setting_name)
				all_widgets.extend([wid])	
			
			if len(instance.settings)>0: layout_main.addWidget(grp_settings)

	# line separator
	line = QtWidgets.QFrame()
	line.setFrameShape(QtWidgets.QFrame.HLine)
	layout_main.addWidget(line)
	all_widgets.extend([line])

	# delete stream signal
	btn_delete.clicked.connect(lambda: caller.RemoveStream(stream['id'], all_widgets, layout_main))

	return layout_main


