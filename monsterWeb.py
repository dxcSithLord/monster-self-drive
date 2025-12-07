#!/usr/bin/env python
# coding: Latin-1

# Creates a web-page interface for MonsterBorg

# Import library functions we need
import ThunderBorg
import time
import sys
import os
import threading
import socketserver
import picamera
import picamera.array
import cv2
import datetime

# Settings for the web-page
webPort = 8080                            # Port number for the web-page, 80 is what web-pages normally use
webBindAddress = '127.0.0.1'            # Security: Bind to localhost only (use '0.0.0.0' to allow external access - NOT recommended)
imageWidth = 240                        # Width of the captured image in pixels
imageHeight = 192                       # Height of the captured image in pixels
frameRate = 30                          # Number of images to capture per second
displayRate = 10                        # Number of images to request per second
# Security: Use expanduser instead of hardcoded username path
photoDirectory = os.path.expanduser('~/monster-photos')  # Directory to save photos to
flippedCamera = True                    # Swap between True and False if the camera image is rotated by 180
jpegQuality = 80                        # JPEG quality level, smaller is faster, higher looks better (0 to 100)

# Global values (no need for global declaration at module level)
running = True
lastFrame = None
lockFrame = None
camera = None
processor = None
watchdog = None

TB = ThunderBorg.ThunderBorg()
#TB.i2cAddress = 0x15                  # Uncomment and change the value if you have changed the board address
TB.Init()
if not TB.foundChip:
    boards = ThunderBorg.ScanForThunderBorg()
    if len(boards) == 0:
        print('No ThunderBorg found, check you are attached :)')
    else:
        print('No ThunderBorg at address %02X, but we did find boards:' % (TB.i2cAddress))
        for board in boards:
            print('    %02X (%d)' % (board, board))
        print('If you need to change the I2C address change the setup line so it is correct, e.g.')
        print('TB.i2cAddress = 0x%02X' % (boards[0]))
    sys.exit()
TB.SetCommsFailsafe(False)
TB.SetLedShowBattery(False)
TB.SetLeds(0,0,1)

# Power settings
voltageIn = 1.2 * 10                    # Total battery voltage to the ThunderBorg
voltageOut = 12.0 * 0.95                # Maximum motor voltage, we limit it to 95% to allow the RPi to get uninterrupted power

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Timeout thread
class Watchdog(threading.Thread):
    def __init__(self):
        super(Watchdog, self).__init__()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.timestamp = time.time()

    def run(self):
        timedOut = True
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for a network event to be flagged for up to one second
            if timedOut:
                if self.event.wait(1):
                    # Connection
                    print('Reconnected...')
                    TB.SetLedShowBattery(True)
                    timedOut = False
                    self.event.clear()
            else:
                if self.event.wait(1):
                    self.event.clear()
                else:
                    # Timed out
                    print('Timed out...')
                    TB.SetLedShowBattery(False)
                    TB.SetLeds(0,0,1)
                    timedOut = True
                    TB.MotorsOff()

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        """
        Initialize the StreamProcessor thread and prepare its camera buffer and control flags.
        
        Sets up:
        - `stream`: a PiRGBArray bound to the module-level `camera` for receiving frames.
        - `event`: threading.Event used to signal when a new frame is available for processing.
        - `terminated`: boolean flag (False) indicating the thread should continue running.
        - `begin`: numeric counter initialized to 0.
        
        The constructor also starts the thread so it begins processing when signaled.
        """
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)  # noqa: F821
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.begin = 0

    def run(self):
        """
        Continuously waits for frames, encodes the latest camera frame to JPEG, and updates 
        the module-global `lastFrame`.
        
        While `self.terminated` is False, waits up to one second for `self.event` to be set.
        When set, reads the current frame from `self.stream`, optionally flips it according 
        to `flippedCamera`, encodes it to JPEG with `jpegQuality`, and replaces the 
        module-global `lastFrame` while holding `lockFrame`. After processing, resets the 
        stream and clears the event.
        """
        global lastFrame  # Assigned when frame changes
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and save globally
                    self.stream.seek(0)
                    if flippedCamera:
                        flippedArray = cv2.flip(self.stream.array, -1)  # Flips X and Y
                        retval, thisFrame = cv2.imencode('.jpg', flippedArray, [cv2.IMWRITE_JPEG_QUALITY, jpegQuality])
                        if not retval:
                            continue  # Skip this frame
                        del flippedArray
                    else:
                        retval, thisFrame = cv2.imencode('.jpg', self.stream.array, [cv2.IMWRITE_JPEG_QUALITY, jpegQuality])
                        if not retval:
                            continue  # Skip this frame

                    # updated to resolve a possible concurrency bug.
                    # Use a context manager to guarantee the lock is always released
                    with lockFrame:
                        lastFrame = thisFrame
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        """
        Initialize the ImageCapture thread and start it.
        
        Creates the thread instance responsible for driving the camera capture loop and 
        begins its execution immediately.
        """
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        # camera and processor are read-only, no global needed
        """
        Capture a continuous video stream from the camera and coordinate shutdown of the 
        frame processor.
        
        Starts camera capture using the camera's video port; when capture completes, marks 
        the processor as terminated and waits for the processor thread to finish.
        """
        print('Start the stream using the video port')
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)  # noqa: F821
        print('Terminating camera processing...')
        processor.terminated = True
        processor.join()
        print('Processing terminated.')

    # Stream delegation loop
    def TriggerStream(self):
        # running and processor are read-only, no global needed
        """
        Provide a generator for the camera capture loop that yields the processor's frame 
        buffer whenever the processor is ready.
        
        Returns:
            generator: Yields the current `processor.stream` object each time a new frame 
            buffer should be captured while the module-level `running` flag is True.
        """
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Class used to implement the web server
class WebServer(socketserver.BaseRequestHandler):
    def handle(self):
        # TB, lastFrame, lockFrame, watchdog are read-only, no global needed
        # Get the HTTP request data
        """
        Handle a single incoming HTTP request and respond to camera, motor, and control 
        endpoints.
        
        Processes the raw HTTP request from the connection and routes based on the request 
        path. Supported behaviors include:
        - Serving the latest camera JPEG (/cam.jpg).
        - Stopping motors (/off) and setting motor power (/set/<left>/<right>).
        - Saving a timestamped photo to the configured photo directory (/photo) with path 
          validation and error handling.
        - Serving the main control pages (/, /hold) and the streaming page (/stream).
        This method also signals activity to the watchdog, reads the current frame under 
        lock, and may change motor state or write files as described.
        """
        reqData = self.request.recv(1024).strip()
        reqData = reqData.decode('utf-8').split('\n')
        # Get the URL requested
        getPath = ''
        for line in reqData:
            if line.startswith('GET'):
                parts = line.split(' ')
                getPath = parts[1]
                break
        watchdog.event.set()
        if getPath.startswith('/cam.jpg'):
            # Camera snapshot
            with lockFrame:
                sendFrame = lastFrame
            if sendFrame is not None:
                self.send(sendFrame.tobytes())
        elif getPath.startswith('/off'):
            # Turn the drives off
            httpText = '<html><body><center>'
            httpText += 'Speeds: 0 %, 0 %'
            httpText += '</center></body></html>'
            self.send(httpText)
            TB.MotorsOff()
        elif getPath.startswith('/set/'):
            # Motor power setting: /set/driveLeft/driveRight
            parts = getPath.split('/')
            # Get the power levels
            if len(parts) >= 4:
                try:
                    driveLeft = float(parts[2])
                    driveRight = float(parts[3])
                except:
                    # Bad values
                    driveRight = 0.0
                    driveLeft = 0.0
            else:
                # Bad request
                driveRight = 0.0
                driveLeft = 0.0
            # Ensure settings are within limits
            if driveRight < -1:
                driveRight = -1
            elif driveRight > 1:
                driveRight = 1
            if driveLeft < -1:
                driveLeft = -1
            elif driveLeft > 1:
                driveLeft = 1
            # Report the current settings
            percentLeft = driveLeft * 100.0;
            percentRight = driveRight * 100.0;
            httpText = '<html><body><center>'
            httpText += 'Speeds: %.0f %%, %.0f %%' % (percentLeft, percentRight)
            httpText += '</center></body></html>'
            self.send(httpText)
            # Set the outputs
            driveLeft *= maxPower
            driveRight *= maxPower
            TB.SetMotor1(driveRight)
            TB.SetMotor2(driveLeft)
        elif getPath.startswith('/photo'):
            # Save camera photo
            with lockFrame:
                captureFrame = lastFrame
            httpText = '<html><body><center>'
            if captureFrame is not None:
                # Security: Create safe photo path and ensure directory exists
                try:
                    # Ensure photo directory exists
                    os.makedirs(photoDirectory, exist_ok=True)
                    # Create safe filename
                    filename = 'Photo_%s.jpg' % datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    base_dir = os.path.abspath(photoDirectory)
                    photoName = os.path.join(base_dir, filename)
                    # Validate path is within photoDirectory (prevent path traversal)
                    # Use os.path.commonpath for robust containment check
                    if os.path.commonpath([photoName, base_dir]) != base_dir:
                        raise ValueError('Invalid photo path')
                    # Save photo
                    photoFile = open(photoName, 'wb')
                    photoFile.write(captureFrame)
                    photoFile.close()
                    httpText += 'Photo saved to %s' % (photoName)
                except (IOError, OSError, ValueError) as e:
                    # Security: Use specific exceptions and don't expose details to user
                    httpText += 'Failed to take photo!'
                    print('Photo save error: %s' % str(e))
            else:
                httpText += 'Failed to take photo!'
            httpText += '</center></body></html>'
            self.send(httpText)
        elif getPath == '/':
            # Main page, click buttons to move and to stop
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            httpText += '<button onclick="Drive(-1,1)" style="width:200px;height:100px;"><b>Spin Left</b></button>\n'
            httpText += '<button onclick="Drive(1,1)" style="width:200px;height:100px;"><b>Forward</b></button>\n'
            httpText += '<button onclick="Drive(1,-1)" style="width:200px;height:100px;"><b>Spin Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Drive(0,1)" style="width:200px;height:100px;"><b>Turn Left</b></button>\n'
            httpText += '<button onclick="Drive(-1,-1)" style="width:200px;height:100px;"><b>Reverse</b></button>\n'
            httpText += '<button onclick="Drive(1,0)" style="width:200px;height:100px;"><b>Turn Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Off()" style="width:200px;height:100px;"><b>Stop</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:200px;height:100px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<input id="speed" type="range" min="0" max="100" value="100" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
        elif getPath == '/hold':
            # Alternate page, hold buttons to move (does not work with all devices)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            httpText += '<button onmousedown="Drive(-1,1)" onmouseup="Off()" style="width:200px;height:100px;"><b>Spin Left</b></button>\n'
            httpText += '<button onmousedown="Drive(1,1)" onmouseup="Off()" style="width:200px;height:100px;"><b>Forward</b></button>\n'
            httpText += '<button onmousedown="Drive(1,-1)" onmouseup="Off()" style="width:200px;height:100px;"><b>Spin Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onmousedown="Drive(0,1)" onmouseup="Off()" style="width:200px;height:100px;"><b>Turn Left</b></button>\n'
            httpText += '<button onmousedown="Drive(-1,-1)" onmouseup="Off()" style="width:200px;height:100px;"><b>Reverse</b></button>\n'
            httpText += '<button onmousedown="Drive(1,0)" onmouseup="Off()" style="width:200px;height:100px;"><b>Turn Right</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:200px;height:100px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            httpText += '<input id="speed" type="range" min="0" max="100" value="100" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
        elif getPath == '/stream':
            # Streaming frame, set a delayed refresh
            displayDelay = int(1000 / displayRate)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function refreshImage() {\n'
            httpText += ' if (!document.images) return;\n'
            httpText += ' document.images["rpicam"].src = "cam.jpg?" + Math.random();\n'
            httpText += ' setTimeout("refreshImage()", %d);\n' % (displayDelay)
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body onLoad="setTimeout(\'refreshImage()\', %d)">\n' % (displayDelay)
            httpText += '<center><img src="/cam.jpg" style="width:600;height:480;" name="rpicam" /></center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
        else:
            # Unexpected page
            self.send('Path : "%s"' % (getPath))

    def send(self, content):
        if type(content) == bytes:
            h_head = b'HTTP/1.0 200 OK\n\n' + content
        elif type(content) == str:
            h_head = b'HTTP/1.0 200 OK\n\n' + content.encode('utf-8')
        self.request.sendall(h_head)
        #self.request.sendall('HTTP/1.0 200 OK\n\n%s' % (content.encode('utf-8')))


# Create the image buffer frame
lastFrame = None
lockFrame = threading.Lock()

# Startup sequence
print('Setup camera')
camera = picamera.PiCamera()
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate

print('Setup the stream processing thread')
processor = StreamProcessor()

print('Wait ...')
time.sleep(2)
captureThread = ImageCapture()

print('Setup the watchdog')
watchdog = Watchdog()

# Run the web server until we are told to close
try:
    httpServer = None
    # Security: Bind to configured address (default localhost for security)
    print('Starting web server on %s:%d' % (webBindAddress, webPort))
    if webBindAddress == '0.0.0.0':
        print('WARNING: Server is exposed on ALL network interfaces!')
        print('         This is a SECURITY RISK - consider using localhost or specific IP')
    httpServer = socketserver.TCPServer((webBindAddress, webPort), WebServer)
except (OSError, IOError) as e:
    # Security: Use specific exceptions instead of bare except
    # Failed to open the port, report common issues
    print()
    print('Failed to open port %d: %s' % (webPort, str(e)))
    print('Make sure you are running the script with sudo permissions')
    print('Other problems include running another script with the same port')
    print('If the script was just working recently try waiting a minute first')
    print()
    # Flag the script to exit
    running = False
try:
    print('Press CTRL+C to terminate the web-server')
    while running:
        httpServer.handle_request()
except KeyboardInterrupt:
    # CTRL+C exit
    print('\nUser shutdown')
finally:
    # Turn the motors off under all scenarios
    TB.MotorsOff()
    print('Motors off')
# Tell each thread to stop, and wait for them to end
if httpServer != None:
    httpServer.server_close()
running = False
captureThread.join()
processor.terminated = True
watchdog.terminated = True
processor.join()
watchdog.join()
del camera
TB.SetLedShowBattery(False)
TB.SetLeds(0,0,0)
TB.MotorsOff()
print('Web-server terminated.')
