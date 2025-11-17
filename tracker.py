import cv2
import numpy as np
import time
import serial
import os
import config as cfg

# --- Load Color Configuration ---
ccfg = None
color_config_path = os.path.join(os.path.dirname(__file__), 'color_config.py')
if os.path.exists(color_config_path):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("color_config", color_config_path)
        ccfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ccfg)
        GREEN_LOWER = ccfg.GREEN_LOWER
        GREEN_UPPER = ccfg.GREEN_UPPER
        print("Successfully loaded custom color configuration from 'color_config.py'.")
    except Exception as e:
        GREEN_LOWER = cfg.GREEN_LOWER
        GREEN_UPPER = cfg.GREEN_UPPER
        print(f"Could not load 'color_config.py': {e}")
        print("Using default color configuration from 'config.py'.")
        print("Tip: Run 'color_calibration.py' to fine-tune color detection.")
else:
    GREEN_LOWER = cfg.GREEN_LOWER
    GREEN_UPPER = cfg.GREEN_UPPER
    print("Using default color configuration from 'config.py'.")
    print("Tip: Run 'color_calibration.py' to fine-tune color detection.")

# --- Load Distance Estimation Model ---
try:
    calibration_data = np.load(cfg.CALIBRATION_FILE)
    pixel_widths = calibration_data[:, 0]
    distances = calibration_data[:, 1]
    distance_model = np.poly1d(np.polyfit(pixel_widths, distances, 2))
    print(f"Successfully loaded distance calibration from '{cfg.CALIBRATION_FILE}'.")
except FileNotFoundError:
    print(f"Warning: Distance calibration file '{cfg.CALIBRATION_FILE}' not found.")
    print("Run 'position_calibration.py' to create it. Distance will not be shown.")
    distance_model = None
except Exception as e:
    print(f"Warning: Could not process distance calibration file: {e}")
    distance_model = None

# --- Load Camera Properties for Tracking ---
try:
    cam_props = np.load(cfg.CAMERA_PROPERTIES_FILE, allow_pickle=True).item()
    PAN_SLOPE = cam_props['pan_slope']
    PAN_INTERCEPT = cam_props['pan_intercept']
    TILT_SLOPE = cam_props['tilt_slope']
    TILT_INTERCEPT = cam_props['tilt_intercept']
    
    # Load servo limits, with defaults if they don't exist
    PAN_MIN = cam_props.get('pan_min', 0)
    PAN_MAX = cam_props.get('pan_max', 180)
    TILT_MIN = cam_props.get('tilt_min', 0)
    TILT_MAX = cam_props.get('tilt_max', 180)

    print(f"Successfully loaded camera properties from '{cfg.CAMERA_PROPERTIES_FILE}'.")
    print(f"  - Pan Model: angle = {PAN_SLOPE:.4f}*x + {PAN_INTERCEPT:.4f}")
    print(f"  - Tilt Model: angle = {TILT_SLOPE:.4f}*y + {TILT_INTERCEPT:.4f}")
    if 'pan_min' not in cam_props:
        print("  - Warning: Servo pan/tilt limits not found. Using defaults (0-180).")
        print("  - Tip: Run 'position_calibration.py' (Option 3) to set custom limits.")
    else:
        print(f"  - Servo Pan Limits: ({PAN_MIN}, {PAN_MAX})")
        print(f"  - Servo Tilt Limits: ({TILT_MIN}, {TILT_MAX})")

except FileNotFoundError:
    print(f"Error: Camera properties file '{cfg.CAMERA_PROPERTIES_FILE}' not found.")
    print("Please run 'position_calibration.py' (Option 1: Servo-Pixel Mapping) to generate it.")
    exit()
except KeyError as e:
    print(f"Error: Missing expected property {e} in '{cfg.CAMERA_PROPERTIES_FILE}'.")
    print("Your calibration file is outdated. Please run 'position_calibration.py' (Option 1) again.")
    exit()
except Exception as e:
    print(f"An error occurred while loading the camera properties file: {e}")
    exit()

# --- Kalman Filter Initialization ---
kalman = cv2.KalmanFilter(4, 2)
kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
kalman.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
kalman.processNoiseCov = np.eye(4, dtype=np.float32) * cfg.KALMAN_PROCESS_NOISE
kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * cfg.KALMAN_MEASUREMENT_NOISE

# --- Serial Communication Setup ---
try:
    ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Serial port {cfg.SERIAL_PORT} opened successfully.")
except serial.SerialException as e:
    print(f"Error opening serial port {cfg.SERIAL_PORT}: {e}")
    ser = None

# --- Servo Angle Initialization ---
pan_angle = 90.0
tilt_angle = 90.0
last_sent_pan = int(pan_angle)
last_sent_tilt = int(tilt_angle)

def send_servo_command(pan, tilt):
    """Sends the servo angles to the Arduino if they've changed enough."""
    global last_sent_pan, last_sent_tilt
    pan_int, tilt_int = int(pan), int(tilt)
    
    if ser and (abs(pan_int - last_sent_pan) >= cfg.ANGLE_THRESHOLD or abs(tilt_int - last_sent_tilt) >= cfg.ANGLE_THRESHOLD):
        command = f"{pan_int},{tilt_int}\n"
        ser.write(command.encode())
        # print(f"Sent command: {command.strip()}") # Uncomment for debugging
        last_sent_pan, last_sent_tilt = pan_int, tilt_int

# --- Camera Setup ---
cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
if not cap.isOpened():
    print(f"Error: Could not open camera at index {cfg.CAMERA_INDEX}.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, cfg.TARGET_FPS)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
center_x, center_y = frame_width // 2, frame_height // 2
print(f"Camera resolution set to: {frame_width}x{frame_height}")
print("--- Tracking Started ---")
print("Press 'q' in the window to exit.")

# --- Main Tracking Loop ---
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break


    # Mirror the frame for a more intuitive view
    # frame = cv2.flip(frame, 1)

    if cfg.USE_GPU:
        gpu_frame = cv2.UMat(frame)
        hsv = cv2.cvtColor(gpu_frame, cv2.COLOR_BGR2HSV)
    else:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:
        largest_contour = max(contours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)

        if radius > 10:
            # Kalman Filter Prediction and Correction
            kalman.predict()
            measurement = np.array([np.float32(x), np.float32(y)])
            kalman.correct(measurement)
            predicted_state = kalman.statePost
            x, y = predicted_state[0:2].flatten()

            # --- Distance Estimation (for display) ---
            if distance_model is not None:
                pixel_width = radius * 2
                estimated_distance = distance_model(pixel_width)
                dist_text = f"Dist: {estimated_distance:.1f} cm"
                cv2.putText(frame, dist_text, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # --- Servo Control ---
            # Calculate target angles directly from the new model
            target_pan = (x * PAN_SLOPE) + PAN_INTERCEPT
            target_tilt = (y * TILT_SLOPE) + TILT_INTERCEPT

            # Apply smoothing
            pan_angle = (1 - cfg.SMOOTHING_FACTOR) * pan_angle + cfg.SMOOTHING_FACTOR * target_pan
            tilt_angle = (1 - cfg.SMOOTHING_FACTOR) * tilt_angle + cfg.SMOOTHING_FACTOR * target_tilt
            
            # Clip to servo limits
            pan_angle = np.clip(pan_angle, PAN_MIN, PAN_MAX)
            tilt_angle = np.clip(tilt_angle, TILT_MIN, TILT_MAX)
            
            send_servo_command(pan_angle, tilt_angle)
            
            # Draw tracking visuals
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
            cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)

    # --- Display Information ---
    angle_text = f"Pan: {int(pan_angle)} Tilt: {int(tilt_angle)}"
    cv2.putText(frame, angle_text, (10, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.line(frame, (center_x - 15, center_y), (center_x + 15, center_y), (0, 0, 255), 2)
    cv2.line(frame, (center_x, center_y - 15), (center_x, center_y + 15), (0, 0, 255), 2)
    
    cv2.imshow('Object Tracker', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Cleanup ---
print("\nExiting...")
if ser:
    # Center the servos on exit
    ser.write("90,90\n".encode())
    time.sleep(0.1)
    ser.close()
    print("Serial port closed.")

cap.release()
cv2.destroyAllWindows()
print("Camera released and windows closed.")
