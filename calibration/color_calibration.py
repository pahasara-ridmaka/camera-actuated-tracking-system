import cv2
import numpy as np
import os

# --- Configuration ---
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CONFIG_FILE = 'color_config.py'

def nothing(x):
    """Dummy function for trackbar creation."""
    pass

def main():
    """
    Main function to run the color calibration utility.
    """
    # --- Camera Setup ---
    cap = cv2.VideoCapture("http://172.20.10.1:4747/video")
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {CAMERA_INDEX}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    print(f"Camera opened successfully ({FRAME_WIDTH}x{FRAME_HEIGHT}).")

    # --- UI Setup ---
    cv2.namedWindow('Color Calibration')
    cv2.createTrackbar('H_L', 'Color Calibration', 35, 179, nothing)
    cv2.createTrackbar('S_L', 'Color Calibration', 100, 255, nothing)
    cv2.createTrackbar('V_L', 'Color Calibration', 100, 255, nothing)
    cv2.createTrackbar('H_U', 'Color Calibration', 85, 179, nothing)
    cv2.createTrackbar('S_U', 'Color Calibration', 255, 255, nothing)
    cv2.createTrackbar('V_U', 'Color Calibration', 255, 255, nothing)

    print("\n--- Instructions ---")
    print("1. Adjust the trackbars to isolate the desired color.")
    print("2. The 'Mask' window should show the target object in white and the rest in black.")
    print("3. Press 's' to save the current values to a configuration file.")
    print("4. Press 'q' to quit the program.")
    print("--------------------")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break

        # Get current trackbar positions
        h_l = cv2.getTrackbarPos('H_L', 'Color Calibration')
        s_l = cv2.getTrackbarPos('S_L', 'Color Calibration')
        v_l = cv2.getTrackbarPos('V_L', 'Color Calibration')
        h_u = cv2.getTrackbarPos('H_U', 'Color Calibration')
        s_u = cv2.getTrackbarPos('S_U', 'Color Calibration')
        v_u = cv2.getTrackbarPos('V_U', 'Color Calibration')

        lower_bound = np.array([h_l, s_l, v_l])
        upper_bound = np.array([h_u, s_u, v_u])

        # --- Image Processing ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Optional: Apply morphology to reduce noise
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        result = cv2.bitwise_and(frame, frame, mask=mask)

        # --- Display ---
        cv2.imshow('Original', frame)
        cv2.imshow('Mask', mask)
        cv2.imshow('Result', result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_config(lower_bound, upper_bound)

    # --- Cleanup ---
    cap.release()
    cv2.destroyAllWindows()
    print("Calibration finished.")

def save_config(lower, upper):
    """
    Saves the color configuration to a Python file.
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write("# --- Auto-generated Color Configuration ---\n")
            f.write("import numpy as np\n\n")
            f.write(f"GREEN_LOWER = np.array([{lower[0]}, {lower[1]}, {lower[2]}])\n")
            f.write(f"GREEN_UPPER = np.array([{upper[0]}, {upper[1]}, {upper[2]}])\n")
        print(f"\\n[SUCCESS] Configuration saved to '{CONFIG_FILE}'")
        print(f"  - Lower Bound: {lower}")
        print(f"  - Upper Bound: {upper}\n")
    except Exception as e:
        print(f"\\n[ERROR] Could not save configuration to '{CONFIG_FILE}': {e}\\n")

if __name__ == '__main__':
    main()
