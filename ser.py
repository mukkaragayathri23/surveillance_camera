import cv2
from cv2 import VideoWriter
from cv2 import VideoWriter_fourcc
from twilio.rest import Client
import socketserver
from http import server
import threading
import time
import datetime
import numpy as np

# Your Twilio Account SID and Auth Token
TWILIO_ACCOUNT_SID = 'AC88c082c048e0764cc9c5d0a5a96312ec'
TWILIO_AUTH_TOKEN = '2c620a31441942f4da43fbe6a57bf5ef'

# Your Twilio phone number and the destination phone number
TWILIO_PHONE_NUMBER = '+12762860929'
DESTINATION_PHONE_NUMBER = '+916309133957'

# Load the reference image
reference_image = cv2.imread('abc.jpg')

# Get the dimensions of the reference image
reference_height, reference_width, _ = reference_image.shape

# Initialize the video capture and video writer

v = VideoWriter('output_video.avi', VideoWriter_fourcc(*'XVID'), 15.0, (reference_width, reference_height), isColor=True)
# Initialize the Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Define a cooldown period (in seconds) to control message frequency
cooldown_period = 3600  # Adjust this as needed (e.g., 60 seconds)

# Initialize a timestamp for the last message sent
last_message_time = 0

# Directory to save images when a difference is detected
image_save_directory = 'difference_images/'

# Create the directory if it doesn't exist
import os
os.makedirs(image_save_directory, exist_ok=True)

# Initialize a timestamp for the last image saved
last_image_save_time = 0

# Global variable for last_message_time
last_message_time = 0

def capture_frames(server):
    global last_message_time  # Declare last_message_time as global
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if ret:
            server.frame = frame
            time.sleep(0.001)  # Control frame capture rate
        else:
            server.frame = None

PAGE = """\
<html>
<head>
<title>Webcam Stream</title>
<style>
.row::after {
  content: "";
  clear: both;
  display: table;
}
.column {
  float: left;
  width: 33.33%;
  padding: 5px;
}
</style>
</head>
<body>
<center><h1>Webcam Stream</h1></center>
<div class="row">
  <div class="column">
    <img src="stream.mjpg" width="95%" height="100%">
  </div>
  <div class="column">
    <img src="stream1.mjpg" width="100%" height="100%">
  </div>
</div>
</body>
</html>
"""

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            last_message_time = 0
            try:
                while True:
                    if self.server.frame is not None:
                        frame = self.server.frame
                        frame=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frame=cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        timestamp = datetime.datetime.now() .strftime("%Y-%m-%d %H:%M:%S")
                        cv2.putText(frame,timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0, 2))
                        _, img_encoded = cv2.imencode('.jpg', frame)
                        frame_data = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + img_encoded.tobytes() + b'\r\n'
                        self.wfile.write(frame_data)
                        frame = cv2.resize(frame, (reference_width, reference_height))
                        diff = cv2.absdiff(reference_image, frame)
                        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                        mean_diff = cv2.mean(gray_diff)[0]
                        threshold = 20

                        if mean_diff > threshold:
                            v.write(frame)
                            
                            current_time = time.time()
                            if current_time - last_message_time >= cooldown_period:
                                # Send an SMS using Twilio
                                message = client.messages.create(
                                    body="A difference was detected in the video! check out this ip address http://127.0.0.1:8001/ http://192.168.83.120:8001/",
                                    from_=TWILIO_PHONE_NUMBER,
                                    to=DESTINATION_PHONE_NUMBER)
                            # Update the timestamp of the last message sent
                            last_message_time = current_time
                            
                    else:
                        time.sleep(0.001)  # Wait for a new frame
            except Exception as e:
                print(e)
                return
        elif self.path == "/stream1.mjpg":
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    if self.server.frame is not None:
                        frame = self.server.frame
                        _, img_encoded = cv2.imencode('.jpg', frame)
                        frame_data = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + img_encoded.tobytes() + b'\r\n'
                        self.wfile.write(frame_data)
                    else:
                        time.sleep(0.001)  # Wait for a new frame
            except Exception as e:
                print(e)
                return
        else:
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    frame = None

if __name__ == '__main__':
    address = ('', 8001)
    server = StreamingServer(address, StreamingHandler)
    v = VideoWriter('output_video.avi', VideoWriter_fourcc(*'XVID'), 25.0, (reference_width, reference_height), isColor=True)
    
    # Start the frame capture thread
    frame_thread = threading.Thread(target=capture_frames, args=(server,))
    frame_thread.daemon = True
    frame_thread.start()

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print("Server started")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
        v.release()
        print("Server stopped")
