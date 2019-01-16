import random
import tkinter as tk
import cv2
import time
import PIL.Image
import PIL.ImageTk
import serial

from tkinter import ttk
from tkinter import filedialog

import face_recognition


def train_image(image_path, name):
	image = face_recognition.load_image_file(image_path)
	try:
		face_encoding = face_recognition.face_encodings(image)[0]
	except IndexError:
		return None, None
	# Create arrays of known face encodings and their names
	known_face_encodings = [
		face_encoding,
	]
	known_face_names = [
		name,
	]
	return known_face_encodings, known_face_names


class InterfaceProgram:
	counter = 0

	def __init__(self, video_source=0):
		self.window = tk.Tk()
		self.window.title("Nhận diện khuôn mặt ứng dụng cho mở cửa nhà")
		self.window2 = None
		self.after_job = None

		# init para
		self.face_name_per_time = []
		self.loss = 0.0
		self.detect_name = ""
		self.is_detect = False
		self.sleep = False
		self.temp = 0
		self.temp_list = []
		self.new_time = time.time()
		self.old_time = time.time()
		self.process_this_frame = True
		self.my_name = None
		self.is_show = False

		self.ser = serial.Serial('COM3', baudrate=112500, timeout=1)
		self.ser.close()
		self.ser.open()

		self.video_source = video_source
		# open video source (by default this will try to open the computer webcam)
		self.vid = MyVideoCapture(self.video_source)

		self.known_face_encodings, self.known_face_names = train_image(image_path="images/train_image.jpg", name="Owner")
		if self.known_face_encodings is None and self.known_face_names is None:
			self.is_status = False
		else:
			self.is_status = True
		# Create frame
		self.cmd_frame = ttk.LabelFrame(self.window, text="Commands", relief=tk.RIDGE)
		self.cmd_frame.grid(row=1, column=1, sticky=tk.E + tk.W + tk.N + tk.S)

		self.entry_frame = ttk.LabelFrame(self.window, text="Camera", relief=tk.RIDGE)
		self.entry_frame.grid(row=2, column=1, sticky=tk.E + tk.W + tk.N + tk.S)
		# Create a canvas that can fit the above video source size
		self.canvas = tk.Canvas(self.entry_frame, width=self.vid.width, height=self.vid.height)

		self.create_widgets()
		self.delay = 15
		self.update()

	def snapshot(self):
		# Get a frame from the video source
		ret, frame = self.vid.get_frame()

		if ret:
			cv2.imwrite("images/train_image.jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

	def update_for_window2(self):
		# Get a frame from the video source
		ret, frame = self.vid.get_frame()

		if ret:
			self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
			self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

		self.after_job = self.window.after(self.delay, self.update_for_window2)

	def update(self):
		# Get a frame from the video source
		font = cv2.FONT_HERSHEY_DUPLEX
		self.new_time = time.time()
		ret, frame = self.vid.get_frame()

		# Resize frame of video to 1/4 size for faster face recognition processing
		small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

		# Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
		rgb_small_frame = small_frame[:, :, ::-1]
		if self.process_this_frame:
			face_locations = face_recognition.face_locations(rgb_small_frame)
			face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
			face_names = []

			for face_encoding in face_encodings:
				# See if the face is a match for the known face(s)
				
				name = "Unknown"
				if self.is_status:
					matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.4)
					# If a match was found in known_face_encodings, just use the first one.
					if True in matches:
						first_match_index = matches.index(True)
						name = self.known_face_names[first_match_index]
				else:
					cv2.putText(frame, 'Train error! Train again, please.', (50, 50), font, 1.0, (255, 255, 255), 1)

				face_names.append(name)
			if self.is_detect:
				if len(face_names) > 1:
					self.is_detect = False
					self.is_show = True
			if self.is_show:
				if (self.new_time - self.old_time) < 4:
					cv2.putText(frame, 'Only open the door with one face!', (50, 50), font, 1.0, (255, 0, 0), 1)
				else:
					self.is_show = False

			temp = 0
			for (top, right, bottom, left), name in zip(face_locations, face_names):
				# Scale back up face locations since the frame we detected in was scaled to 1/4 size
				top *= 4
				right *= 4
				bottom *= 4
				left *= 4
				temp += 1

				# Draw a box around the face
				cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
				cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

				if self.is_detect:
					if self.new_time - self.old_time > 2:
						self.is_detect = False
						self.sleep = True
						for iName in self.known_face_names:
							self.loss = float(self.face_name_per_time.count(iName)) / len(self.face_name_per_time)
							if self.loss > 0.5:
								self.detect_name = iName
						self.face_name_per_time = []
					else:
						self.temp += int(left / 20)
						self.face_name_per_time.append(name)
						cv2.rectangle(frame, (left, bottom - 35), (left + self.temp, bottom), (0, 255, 255), cv2.FILLED)
				if self.sleep:
					if self.new_time - self.old_time < 4:
						if self.detect_name in self.known_face_names:
							cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
							cv2.putText(frame, self.detect_name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
							self.ser.write(b'open')
						else:
							cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (255, 0, 0), cv2.FILLED)
							cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
							self.ser.write(b'close')
					else:
						self.sleep = False
						self.detect_name = "Unknown"
		self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
		self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
		# self.process_this_frame = not self.process_this_frame
		self.after_job = self.window.after(self.delay, self.update)

	def train_again_window(self):
		self.window.after_cancel(self.after_job)
		self.after_job = None
		self.window2 = tk.Toplevel()
		self.window2.wm_title("Huấn luyện máy học")
		self.window2['padx'] = 5
		self.window2['pady'] = 5

		cmd_frame = ttk.LabelFrame(self.window2, text="Commands", relief=tk.RIDGE)
		cmd_frame.grid(row=1, column=1, sticky=tk.E + tk.W + tk.N + tk.S)

		button_label = ttk.Label(cmd_frame, text="Chụp một hình khác để huấn luyện:")
		button_label.grid(row=1, column=1, sticky=tk.W, pady=3)
		# Button that lets the user take a snapshot
		self.canvas = tk.Canvas(cmd_frame, width=self.vid.width, height=self.vid.height)
		self.canvas.grid(row=2, column=1)
		self.btn_snapshot = tk.Button(cmd_frame, text="Snapshot", width=30, bg="red", command=self.snapshot)
		self.btn_snapshot.grid(row=2, column=1, sticky=tk.E + tk.W + tk.S)

		cmd_frame2 = ttk.LabelFrame(self.window2, text="Commands", relief=tk.RIDGE)
		cmd_frame2.grid(row=1, column=2, sticky=tk.E + tk.W + tk.N + tk.S)

		self.my_name = ttk.Entry(cmd_frame2, width=40)
		self.my_name.grid(row=2, column=1, sticky=tk.W, pady=3)
		self.my_name.insert(tk.END, "Owner")

		btn_save = tk.Button(cmd_frame2, text="Save", width=10, command=self.train_again)
		btn_save.grid(row=1, column=1)

		# After it is called once, the update method will be automatically called every delay milliseconds
		self.update_for_window2()

	def add_owner_window(self):
		self.window.after_cancel(self.after_job)
		self.after_job = None
		self.window2 = tk.Toplevel()
		self.window2.wm_title("Huấn luyện máy học")
		self.window2['padx'] = 5
		self.window2['pady'] = 5

		cmd_frame = ttk.LabelFrame(self.window2, text="Commands", relief=tk.RIDGE)
		cmd_frame.grid(row=1, column=1, sticky=tk.E + tk.W + tk.N + tk.S)

		button_label = ttk.Label(cmd_frame, text="Chụp một hình khác để huấn luyện:")
		button_label.grid(row=1, column=1, sticky=tk.W, pady=3)
		# Button that lets the user take a snapshot
		self.canvas = tk.Canvas(cmd_frame, width=self.vid.width, height=self.vid.height)
		self.canvas.grid(row=2, column=1)
		self.btn_snapshot = tk.Button(cmd_frame, text="Snapshot", width=30, bg="red", command=self.snapshot)
		self.btn_snapshot.grid(row=2, column=1, sticky=tk.E + tk.W + tk.S)

		cmd_frame2 = ttk.LabelFrame(self.window2, text="Commands", relief=tk.RIDGE)
		cmd_frame2.grid(row=1, column=2, sticky=tk.E + tk.W + tk.N + tk.S)

		self.my_name = ttk.Entry(cmd_frame2, width=40)
		self.my_name.grid(row=2, column=1, sticky=tk.W, pady=3)
		self.my_name.insert(tk.END, "Owner")

		btn_save = tk.Button(cmd_frame2, text="Save", width=10, command=self.train_add)
		btn_save.grid(row=1, column=1)

		# After it is called once, the update method will be automatically called every delay milliseconds
		self.update_for_window2()

	def train_again(self):
		self.window.after_cancel(self.after_job)
		self.after_job = None
		self.known_face_encodings, self.known_face_names = train_image(image_path="images/train_image.jpg", name=self.my_name.get())
		if self.known_face_encodings is None and self.known_face_names is None:
			self.is_status = False
		else:
			self.is_status = True
		self.canvas = tk.Canvas(self.entry_frame, width=self.vid.width, height=self.vid.height)
		self.canvas.grid(row=1, column=1)
		self.update()
		self.window2.destroy()

	def train_add(self):
		self.window.after_cancel(self.after_job)
		self.after_job = None
		known_face_encodings, known_face_names = train_image(image_path="images/train_image.jpg", name=self.my_name.get())
		if not (known_face_encodings is None and known_face_names is None):
			self.known_face_encodings.append(known_face_encodings[0])
			self.known_face_names.append(known_face_names[0])

		self.canvas = tk.Canvas(self.entry_frame, width=self.vid.width, height=self.vid.height)
		self.canvas.grid(row=1, column=1)
		self.update()
		self.window2.destroy()

	def open_door(self):
		self.old_time = time.time()
		if self.is_status:
			self.is_detect = True
		self.temp = 0

	def quit_main_window(self):
		self.window.destroy()
		self.ser.close()

	def create_widgets(self):
		# Create some room around all the internal frames
		self.window['padx'] = 5
		self.window['pady'] = 5

		# - - - - - - - - - - - - - - - - - - - - -
		# The Commands frame
		button_label = tk.Label(self.cmd_frame, bg="yellow", text="Mở cửa:")
		button_label.grid(row=1, column=1, sticky=tk.W, pady=3)

		button_label = tk.Label(self.cmd_frame, bg="yellow", text="Đổi chủ:")
		button_label.grid(row=2, column=1, sticky=tk.W, pady=3)

		my_button = tk.Button(self.cmd_frame, width=20, text="Press", command=self.open_door)
		my_button.grid(row=1, column=2)

		my_button = tk.Button(self.cmd_frame, text="Train again", width=20, command=self.train_again_window)
		my_button.grid(row=2, column=2)

		button_label = tk.Label(self.cmd_frame, bg="yellow", text="Thêm chủ:")
		button_label.grid(row=1, column=3, sticky=tk.W, pady=3, padx=5)

		my_button = tk.Button(self.cmd_frame, width=20, text="Add owner", command=self.add_owner_window)
		my_button.grid(row=1, column=4)

		# - - - - - - - - - - - - - - - - - - - - -
		# The Data entry frame
		self.canvas.grid(row=1, column=1)

		# - - - - - - - - - - - - - - - - - - - - -
		# Menus
		menubar = tk.Menu(self.window)

		filemenu = tk.Menu(menubar, tearoff=0)
		filemenu.add_command(label="Open", command=filedialog.askopenfilename)
		filemenu.add_command(label="Save", command=filedialog.asksaveasfilename)
		filemenu.add_separator()
		filemenu.add_command(label="Exit", command=self.window.quit)
		menubar.add_cascade(label="File", menu=filemenu)

		self.window.config(menu=menubar)

		# - - - - - - - - - - - - - - - - - - - - -
		# Quit button in the lower right corner
		quit_button = ttk.Button(self.window, text="Quit", command=self.quit_main_window)
		quit_button.grid(row=1, column=3)


class MyVideoCapture:
	def __init__(self, video_source=0):
		# Open the video source
		self.vid = cv2.VideoCapture(video_source)
		if not self.vid.isOpened():
			raise ValueError("Unable to open video source", video_source)

		# Get video source width and height
		self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
		self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

	def get_frame(self):
		ret = False
		if self.vid.isOpened():
			ret, frame = self.vid.read()
			frame = cv2.flip(frame, 1)
			if ret:
				# Return a boolean success flag and the current frame converted to BGR
				return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
			else:
				return (ret, None)
		else:
			return (ret, None)

	# Release the video source when the object is destroyed
	def __del__(self):
		if self.vid.isOpened():
			self.vid.release()

	# Create a window and pass it to the Application object


# Create the entire GUI program
program = InterfaceProgram(video_source=0)

# Start the GUI event loop
program.window.mainloop()
