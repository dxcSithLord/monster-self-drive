#!/usr/bin/env python
# coding: Latin-1

#################################################################
# This is the main script for the MonsterBorg self-driving code #
#################################################################

# Load all the library functions we want
import time
import os
import sys
import subprocess
import threading
import cv2
import ThunderBorg
import Settings
import ImageProcessor
print('Libraries loaded')

# Derive some settings from the main settings
if Settings.voltageOut > Settings.voltageIn:
    maxPower = 1.0
else:
    maxPower = Settings.voltageOut / float(Settings.voltageIn)

showFrameDelay = 1.0 / Settings.showPerSecond
waitKeyDelay = int(showFrameDelay * 1000)

# Change the current directory to where this script is
# Security: Use __file__ instead of sys.argv[0] to prevent path manipulation
scriptDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptDir)
print('Running script in directory "%s"' % (scriptDir))

if Settings.testMode:
    print('TEST MODE: Skipping board setup')
else:
    # Setup the ThunderBorg
    global TB
    TB = ThunderBorg.ThunderBorg()
    # TB.i2cAddress = 0x15  # Uncomment and change the value if you have changed the board address
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

    # Blink the LEDs in white to indicate startup
    TB.SetLedShowBattery(False)
    for _ in range(3):
        TB.SetLeds(0, 0, 0)
        time.sleep(0.5)
        TB.SetLeds(1, 1, 1)
        time.sleep(0.5)
    TB.SetLedShowBattery(True)

# Function used by the processing to control the MonsterBorg


def MonsterMotors(driveLeft, driveRight):
    """
    Set left and right motor outputs on the ThunderBorg scaled by the module-level `maxPower`.
    
    Parameters:
        driveLeft (float): Scalar applied to the left motors; multiplied by `maxPower` before being sent to the controller.
        driveRight (float): Scalar applied to the right motors; multiplied by `maxPower` before being sent to the controller.
    """
    TB.SetMotor1(driveRight * maxPower)  # Right side motors
    TB.SetMotor2(driveLeft * maxPower)  # Left side motors

# Function used by the processing for motor output in test mode


def TestModeMotors(driveLeft, driveRight):
    # Convert to percentages
    """
    Print formatted motor power percentages for test mode and advance the internal display counter.
    
    Parameters:
        driveLeft (float): Left motor power as a fraction (expected range -1.0 to 1.0).
        driveRight (float): Right motor power as a fraction (expected range -1.0 to 1.0).
    
    Detailed behavior:
        Scales each input by 100 and prints a line showing the left and right percentages to stdout
        when the internal Settings.testModeCounter reaches Settings.fpsInterval. Advances and resets
        Settings.testModeCounter as needed.
    """
    driveLeft *= 100.0
    driveRight *= 100.0
    # Display at FPS update rate
    Settings.testModeCounter += 1
    if Settings.testModeCounter >= Settings.fpsInterval:
        Settings.testModeCounter = 0
        print('MOTORS: %+07.2f %% left, %+07.2f %% right' % (driveLeft, driveRight))


# Push the appropriate motor function into the settings module
if Settings.testMode:
    Settings.MonsterMotors = TestModeMotors
else:
    Settings.MonsterMotors = MonsterMotors

# Startup sequence
print('Setup camera input')
# Security: Use subprocess instead of os.system to prevent command injection
try:
    subprocess.run(['sudo', 'modprobe', 'bcm2835-v4l2'],
                   check=True,
                   capture_output=True,
                   timeout=5)
except subprocess.CalledProcessError as e:
    print('Warning: Failed to load camera module: %s' % e)
    print('Continuing anyway, camera may already be loaded...')
except subprocess.TimeoutExpired:
    print('Warning: Camera module load timed out')
    print('Continuing anyway...')

Settings.capture = cv2.VideoCapture(0)
# Fix: Use Python 3 OpenCV constants (removed cv2.cv. prefix)
Settings.capture.set(cv2.CAP_PROP_FRAME_WIDTH, Settings.cameraWidth)
Settings.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, Settings.cameraHeight)
Settings.capture.set(cv2.CAP_PROP_FPS, Settings.frameRate)
if not Settings.capture.isOpened():
    Settings.capture.open()
    if not Settings.capture.isOpened():
        print('Failed to open the camera')
        sys.exit()

print('Setup stream processor threads')
Settings.frameLock = threading.Lock()
Settings.processorPool = [ImageProcessor.StreamProcessor(i+1) for i in range(Settings.processingThreads)]
allProcessors = Settings.processorPool[:]

print('Setup control loop')
Settings.controller = ImageProcessor.ControlLoop()

print('Wait ...')
time.sleep(2)
captureThread = ImageProcessor.ImageCapture()

try:
    print('Press CTRL+C to quit')
    Settings.MonsterMotors(0, 0)
    # Create a window to show images if we need one
    if Settings.showImages:
        cv2.namedWindow('Monster view', cv2.WINDOW_NORMAL)
    # Loop indefinitely
    while Settings.running:
        # See if there is a frame to show, wait either way
        monsterView = Settings.displayFrame
        if monsterView is not None:
            if Settings.scaleFinalImage != 1.0:
                size = (int(monsterView.shape[1] * Settings.scaleFinalImage),
                        int(monsterView.shape[0] * Settings.scaleFinalImage))
                monsterView = cv2.resize(monsterView, size, interpolation=cv2.INTER_CUBIC)
            cv2.imshow('Monster view', monsterView)
            cv2.waitKey(waitKeyDelay)
        else:
            # Wait for the interval period
            time.sleep(showFrameDelay)
    # Disable all drives
    Settings.MonsterMotors(0, 0)
except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
    print('\nUser shutdown')
    Settings.MonsterMotors(0, 0)
except Exception as e:
    # Unexpected error, shut down!
    # Security: Use specific exception and don't expose full traceback to users
    print('\nUnexpected error, shutting down!')
    print('Error: %s' % str(e))
    Settings.MonsterMotors(0, 0)
# Tell each thread to stop, and wait for them to end
Settings.running = False
while allProcessors:
    with Settings.frameLock:
        processor = allProcessors.pop()
    processor.terminated = True
    processor.event.set()
    processor.join()
Settings.controller.terminated = True
Settings.controller.join()
captureThread.join()
Settings.capture.release()
del Settings.capture
Settings.MonsterMotors(0, 0)
if not Settings.testMode:
    # Turn the LEDs off to indicate we are done
    TB.SetLedShowBattery(False)
    TB.SetLeds(0, 0, 0)
print('Program terminated.')
