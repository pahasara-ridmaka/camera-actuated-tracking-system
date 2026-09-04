import cv2
import numpy as np
import os
import time
import serial
import config.config as cfg

def get_object_position(cap, lower_bound, upper_bound):
    """
    Finds the center of the largest contour for the specified color range.
    Returns (x, y) position or None if no object is found.
    """
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        return None, None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_bound, upper_bound)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
        if radius > 5:
            # Draw on the frame for user feedback
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
            cv2.putText(frame, "Object Detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            return (int(x), int(y)), frame
            
    cv2.putText(frame, "No object detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return None, frame

def servo_pixel_calibration():
    """
    Guides the user through an interactive calibration to map pixel coordinates to servo angles.
    The user will aim the servos at on-screen targets.
    """
    print("\n--- Servo-Pixel Mapping Calibration ---")
    print("This process will create a model to map screen pixels to servo angles.")

    # --- Serial Setup ---
    try:
        ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Serial port {cfg.SERIAL_PORT} opened successfully.")
    except serial.SerialException as e:
        print(f"Error opening serial port {cfg.SERIAL_PORT}: {e}")
        print("Please ensure the Arduino is connected and the port is correct in config.py.")
        return

    # --- Camera Setup ---
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {cfg.CAMERA_INDEX}.")
        ser.close()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)

    pan_angle, tilt_angle = 90.0, 90.0
    calibration_points = {} # To store {'corner_name': ([pixel_x, pixel_y], [pan, tilt])}

    h, w = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    margin = 50 # Margin from the edge of the frame for calibration points
    
    # --- Calibration Steps ---
    target_pixels = {
        'top_left': (margin, margin),
        'top_right': (w - margin, margin),
        'bottom_right': (w - margin, h - margin),
        'bottom_left': (margin, h - margin),
    }

    # --- Instructions ---
    print("\n--- Calibration Instructions ---")
    print("1. A crosshair target will appear on the screen.")
    print("2. Use 'w', 'a', 's', 'd' keys to move the servo arm (e.g., aiming a laser pointer).")
    print("3. Align the pointer with the CENTER of the on-screen crosshair.")
    print("4. Press 'c' to CAPTURE and save the current servo angles for that target.")
    print("5. Repeat for all four corners.")
    print("6. Press 's' to SAVE the calibration model or 'q' to ABORT.")
    print("---------------------------------\n")

    current_target_name = 'top_left'
    target_iterator = iter(target_pixels.items())
    current_target_name, current_target_pos = next(target_iterator)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Draw all targets
        for name, pos in target_pixels.items():
            color = (0, 255, 0) if name in calibration_points else (0, 0, 255)
            cv2.line(frame, (pos[0] - 10, pos[1]), (pos[0] + 10, pos[1]), color, 2)
            cv2.line(frame, (pos[0], pos[1] - 10), (pos[0], pos[1] + 10), color, 2)

        # Highlight the current target
        if current_target_pos:
            cv2.circle(frame, current_target_pos, 20, (0, 255, 255), 2)
            cv2.putText(frame, f"Aim here: {current_target_name}", (current_target_pos[0] + 15, current_target_pos[1] + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Display info
        info_text = f"Pan: {pan_angle:.1f}, Tilt: {tilt_angle:.1f}"
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, "'c' to capture, 's' to save, 'q' to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Servo Calibration", frame)
        key = cv2.waitKey(1) & 0xFF

        # --- Servo Control ---
        if key == ord('w'): tilt_angle = min(180, tilt_angle + 0.5)
        elif key == ord('s'): tilt_angle = max(0, tilt_angle - 0.5)
        elif key == ord('a'): pan_angle = max(0, pan_angle + 0.5) # Inverted for intuitive control
        elif key == ord('d'): pan_angle = min(180, pan_angle - 0.5) # Inverted for intuitive control
        
        ser.write(f"{int(pan_angle)},{int(tilt_angle)}\n".encode())

        # --- Point Capture ---
        if key == ord('c'):
            if current_target_name:
                calibration_points[current_target_name] = (current_target_pos, (pan_angle, tilt_angle))
                print(f"  -> Captured {current_target_name}: Pixels={current_target_pos}, Angles=({pan_angle:.1f}, {tilt_angle:.1f})")
                try:
                    current_target_name, current_target_pos = next(target_iterator)
                except StopIteration:
                    print("\nAll points captured! Review and press 's' to save or 'q' to abort.")
                    current_target_name, current_target_pos = None, None

        elif key == ord('q'):
            print("Calibration aborted.")
            ser.close()
            cap.release()
            cv2.destroyAllWindows()
            return
        
        elif key == ord('s'):
            if len(calibration_points) == 4:
                break # Proceed to calculation
            else:
                print(f"Cannot save. Please capture all 4 points. Only {len(calibration_points)} captured.")
    
    # --- Calculation ---
    try:
        # Extract data for modeling
        # x_pixels, y_pixels, pan_angles, tilt_angles
        data = np.array([ (p[0][0], p[0][1], p[1][0], p[1][1]) for p in calibration_points.values() ])

        # Fit linear model: pan_angle = m*x_pixel + c
        pan_model = np.polyfit(data[:, 0], data[:, 2], 1)
        pan_slope, pan_intercept = pan_model
        print(f"\nPan Model: angle = {pan_slope:.4f} * pixel_x + {pan_intercept:.4f}")

        # Fit linear model: tilt_angle = m*y_pixel + c
        tilt_model = np.polyfit(data[:, 1], data[:, 3], 1)
        tilt_slope, tilt_intercept = tilt_model
        print(f"Tilt Model: angle = {tilt_slope:.4f} * pixel_y + {tilt_intercept:.4f}")

        # --- Save Properties ---
        # Load existing properties to preserve servo limits if they exist
        if os.path.exists(cfg.CAMERA_PROPERTIES_FILE):
            camera_properties = np.load(cfg.CAMERA_PROPERTIES_FILE, allow_pickle=True).item()
        else:
            camera_properties = {}

        # Update with new model parameters
        camera_properties.update({
            'pan_slope': pan_slope,
            'pan_intercept': pan_intercept,
            'tilt_slope': tilt_slope,
            'tilt_intercept': tilt_intercept,
        })

        np.save(cfg.CAMERA_PROPERTIES_FILE, camera_properties)
        print(f"\n[SUCCESS] Camera properties saved to '{cfg.CAMERA_PROPERTIES_FILE}'")

    except (KeyError, ValueError, ZeroDivisionError) as e:
        print(f"\n[ERROR] Could not calculate mapping. An error occurred: {e}")
        print("Please ensure all four points were captured correctly.")

    # --- Cleanup ---
    ser.write("90,90\n".encode()) # Center servos
    ser.close()
    cap.release()
    cv2.destroyAllWindows()


def distance_calibration():
    """
    Guides the user through collecting data for distance estimation.
    (This function remains unchanged)
    """
    print("\n--- Distance Calibration ---")
    print("This process will create a model to estimate distance based on object size.")
    print("You will need the same object used for tracking.")

    # --- Color Setup ---
    try:
        import config.color_config as ccfg
        lower_bound = ccfg.GREEN_LOWER
        upper_bound = ccfg.GREEN_UPPER
        print("Loaded color configuration from 'color_config.py'.")
    except ImportError:
        lower_bound = cfg.GREEN_LOWER
        upper_bound = cfg.GREEN_UPPER
        print("Using default color configuration from 'config.py'.")
        print("Run 'color_calibration.py' for better results.")

    # --- Camera Setup ---
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {cfg.CAMERA_INDEX}.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)

    calibration_points = []
    
    print("\n--- Instructions ---")
    print("1. Place the object at a known distance from the camera.")
    print("2. Enter the distance when prompted.")
    print("3. The system will record the object's size in pixels.")
    print("4. Repeat for at least 3-5 different distances.")
    print("5. Press 'q' in the camera window when you are finished.")
    print("--------------------\n")

    while True:
        distance_str = input(f"Enter distance to object in CM (or 'done' to finish): ")
        if distance_str.lower() == 'done':
            break
        
        try:
            distance = float(distance_str)
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        print("Detecting object... Press 's' in the window to save this point, or 'n' to skip.")
        
        while True:
            pos, frame = get_object_position(cap, lower_bound, upper_bound)
            
            # We need pixel width for distance, so we re-do contour finding here
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            mask = cv2.erode(mask, None, iterations=2)
            mask = cv2.dilate(mask, None, iterations=2)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            pixel_width = 0
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
                if radius > 5:
                    pixel_width = radius * 2
                    cv2.putText(frame, f"Width: {pixel_width:.2f}px", (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Distance Calibration", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                if pixel_width > 0:
                    calibration_points.append([pixel_width, distance])
                    print(f"  -> Saved point: (Width: {pixel_width:.2f}px, Distance: {distance}cm)")
                    break
                else:
                    print("  -> No object detected. Cannot save point.")
            
            elif key == ord('n'):
                print("  -> Point skipped.")
                break
            
            elif key == ord('q'):
                break
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(calibration_points) < 3:
        print("\n[WARNING] Not enough data points (<3) collected. Calibration not saved.")
        return

    try:
        np.save(cfg.CALIBRATION_FILE, np.array(calibration_points))
        print(f"\n[SUCCESS] Distance calibration data saved to '{cfg.CALIBRATION_FILE}'")
        data = np.array(calibration_points)
        model = np.poly1d(np.polyfit(data[:, 0], data[:, 1], 2))
        print(f"Fitted Model (2nd degree polynomial): \n{model}")
    except Exception as e:
        print(f"\n[ERROR] Could not save calibration data: {e}")

def calibrate_servo_limits():
    """
    Guides the user to find the min/max pan and tilt angles for the visible area.
    """
    print("\n--- Servo Limit Calibration ---")
    print("Use the keys to move the arm to the edges of the camera's view.")
    print("  - 'a'/'d': Pan left/right")
    print("  - 'w'/'s': Tilt up/down")
    print("  - 'z'/'x'/'c'/'v': Save Left/Right/Top/Bottom limits")
    print("  - 'q': Quit")

    # --- Serial Setup ---
    try:
        ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Serial port {cfg.SERIAL_PORT} opened successfully.")
    except serial.SerialException as e:
        print(f"Error opening serial port {cfg.SERIAL_PORT}: {e}")
        return

    # --- Camera Setup ---
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {cfg.CAMERA_INDEX}.")
        ser.close()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)

    pan_angle, tilt_angle = 90, 90
    limits = {
        'pan_min': None, 'pan_max': None,
        'tilt_min': None, 'tilt_max': None
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Display current angles and saved limits
        info_text = f"Pan: {pan_angle}, Tilt: {tilt_angle}"
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        y_offset = 60
        for key, value in limits.items():
            text = f"{key}: {'Not Set' if value is None else value}"
            color = (0, 255, 0) if value is not None else (0, 0, 255)
            cv2.putText(frame, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_offset += 25

        cv2.imshow("Servo Limit Calibration", frame)

        key = cv2.waitKey(1) & 0xFF

        # --- Angle Adjustment ---
        if key == ord('a'): pan_angle = max(0, pan_angle - 1)
        elif key == ord('d'): pan_angle = min(180, pan_angle + 1)
        elif key == ord('w'): tilt_angle = min(180, tilt_angle + 1)
        elif key == ord('s'): tilt_angle = max(0, tilt_angle - 1)
        
        # --- Limit Saving ---
        elif key == ord('z'): 
            limits['pan_min'] = pan_angle
            print(f"Saved pan_min: {pan_angle}")
        elif key == ord('x'): 
            limits['pan_max'] = pan_angle
            print(f"Saved pan_max: {pan_angle}")
        elif key == ord('c'): 
            limits['tilt_max'] = tilt_angle # Tilt is often inverted
            print(f"Saved tilt_max: {tilt_angle}")
        elif key == ord('v'): 
            limits['tilt_min'] = tilt_angle # Tilt is often inverted
            print(f"Saved tilt_min: {tilt_angle}")

        elif key == ord('q'):
            break

        command = f"{pan_angle},{tilt_angle}\n"
        ser.write(command.encode())
        time.sleep(0.02) # Small delay to avoid flooding serial

    # --- Save Data ---
    if any(v is None for v in limits.values()):
        print("\n[WARNING] Not all limits were set. Calibration data not saved.")
    else:
        try:
            # Load existing properties if they exist
            if os.path.exists(cfg.CAMERA_PROPERTIES_FILE):
                camera_properties = np.load(cfg.CAMERA_PROPERTIES_FILE, allow_pickle=True).item()
            else:
                camera_properties = {}
            
            # Update with new limits
            camera_properties.update(limits)

            np.save(cfg.CAMERA_PROPERTIES_FILE, camera_properties)
            print(f"\n[SUCCESS] Servo limits saved to '{cfg.CAMERA_PROPERTIES_FILE}'")
            print(f"  - Pan limits: ({limits['pan_min']}, {limits['pan_max']})")
            print(f"  - Tilt limits: ({limits['tilt_min']}, {limits['tilt_max']})")

        except Exception as e:
            print(f"\n[ERROR] Could not save calibration data: {e}")

    # --- Cleanup ---
    ser.write("90,90\n".encode())
    ser.close()
    cap.release()
    cv2.destroyAllWindows()


def main():
    """
    Main menu for the position calibration utility.
    """
    while True:
        print("\n--- Position Calibration Menu ---")
        print("1. Calibrate Servo-Pixel Mapping")
        print("2. Calibrate Distance Estimation")
        print("3. Calibrate Servo Movement Limits")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == '1':
            servo_pixel_calibration()
        elif choice == '2':
            distance_calibration()
        elif choice == '3':
            calibrate_servo_limits()
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
