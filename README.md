
# Technical Documentation: Camera Actuated Tracking System

## Project Overview

The Camera Actuated Tracking System is a fully automated, precise, and responsive visual servoing loop. It autonomously detects, tracks, and targets objects using computer vision.

-----

## System Architecture & Hardware Components

The system integrates hardware components with serial communication to achieve mechanical tracking.

* **Stationary Camera:** Mounted directly on a pan-tilt mechanism to capture the video feed.
* **Pan-Tilt Mechanism:** Driven by servo motors to physically guide the camera and targeting components.
* **Arduino microcontroller:** Responsible for controlling the servo motors based on received instructions.
* **Laser Pointer:** Attached to the mechanism to provide a clear, visual target lock on the object.
* **Indicator System:** A dedicated setup that reports the current real-time status of the system.

-----

## Software & Signal Processing

The core tracking logic relies on Python, computer vision processing libraries, and predictive filtering.

* **OpenCV Image Processing:** Used to process the incoming video feed from the stationary camera.
* **Object Isolation:** Objects are isolated and distinguished by their unique HSV (Hue, Saturation, Value) color profile.
* **Kalman Filter:** Implemented to predict object motion, ensuring smooth, uninterrupted tracking.
* **Angle Calculation:** A Python script calculates the exact pan and tilt angles required to align with the target.

-----

## System Workflow & Communication

The hardware and software function together in a continuous visual servoing loop:

1. **Detection:** The software processes the video feed via OpenCV and identifies the target by its HSV profile.
2. **Calculation & Transmission:** The Python script computes the necessary servo movements and sends commands to the Arduino over a serial connection.
3. **Actuation:** The Arduino drives the servos, actuating the pan-tilt mechanism to keep the camera and laser locked on the target.
4. **Feedback Loop:** The indicator system updates in real time based on target acquisition.

-----

## System States & Indicators

The indicator system provides real-time feedback regarding operational status:

* **Searching Mode:** Activated automatically when the target is lost or not yet detected.
* **Tracking Mode:** Activated once the target is acquired, confirming that the system has successfully locked onto the object.
