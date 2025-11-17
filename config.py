import numpy as np

# --- General Settings ---
USE_GPU = False  # Set to True to use OpenCV's UMat for GPU acceleration

# --- Serial Communication Settings ---
SERIAL_PORT = 'COM6'  # Change this to your Arduino's serial port
BAUD_RATE = 9600

# --- Camera Settings ---
# Use an IP camera stream (like DroidCam)
CAMERA_INDEX = 'http://172.20.10.1:4747/video'  # URL for DroidCam video feed
# Or, use a physical webcam by index
# CAMERA_INDEX = 0  # 0 for default camera, change if you have multiple cameras
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# --- Color Tracking Settings (to be calibrated) ---
# Default values for green, run color_calibration.py to fine-tune
GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])

# --- Kalman Filter Settings ---
KALMAN_PROCESS_NOISE = 1e-4
KALMAN_MEASUREMENT_NOISE = 1e-1

# --- Servo Control Settings ---
DEAD_ZONE_X = 10  # Pixels from the center horizontally
DEAD_ZONE_Y = 10  # Pixels from the center vertically
SMOOTHING_FACTOR = 0.1  # Reduces jitter, smaller values are smoother
ANGLE_THRESHOLD = 1  # Minimum angle change (in degrees) to send a new command

# --- Calibration File Paths ---
CALIBRATION_FILE = 'distance_calibration.npy'
CAMERA_PROPERTIES_FILE = 'camera_properties.npy'
COLOR_CONFIG_FILE = 'color_config.py'
