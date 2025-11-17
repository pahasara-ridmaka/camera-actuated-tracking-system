#include <Servo.h>

// --- Constants ---
// Servo pins based on user specification
const int PAN_SERVO_PIN = 10; // Base servo
const int TILT_SERVO_PIN = 9;  // Up-down servo

const int LED_LOCKED_PIN = 2;    // LED for when target is successfully tracked
const int LED_SEARCHING_PIN = 3; // LED for when tracking has started and is searching
const int STATUS_OUTPUT_PIN = 5; // Combined status output of pin 2 and 3

// Initial servo positions (center)
const int INITIAL_PAN_ANGLE = 90;
const int INITIAL_TILT_ANGLE = 90;

// --- State and Timing Constants for LEDs ---
const unsigned long SEARCH_TIMEOUT = 1000; // ms to wait before switching to "searching" mode
const int LOCKED_BLINK_INTERVAL = 100;     // Fast blink interval for locked state
const int SEARCHING_BLINK_INTERVAL = 500;  // Slower blink interval for searching state

// --- Global Variables ---
// Create servo objects
Servo panServo;
Servo tiltServo;

// Buffer to store incoming serial data
String serialData;

// State and timing variables for LED blinking
unsigned long lastSerialTime = 0;
unsigned long lastBlinkTime = 0;
bool ledState = false;

void setup() {
  // Start serial communication
  Serial.begin(9600);
  
  pinMode(8, OUTPUT);

  // Set up LED pins as outputs
  pinMode(LED_LOCKED_PIN, OUTPUT);
  pinMode(LED_SEARCHING_PIN, OUTPUT);
  pinMode(STATUS_OUTPUT_PIN, OUTPUT);
  digitalWrite(8, HIGH);

  // Attach servos to their pins
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);
  
  // Move servos to initial positions
  panServo.write(INITIAL_PAN_ANGLE);
  tiltServo.write(INITIAL_TILT_ANGLE);
  
  // Clear any initial garbage data in the serial buffer
  while(Serial.available() > 0) {
    Serial.read();
  }
  
  lastSerialTime = millis(); // Initialize the serial timer

  Serial.println("Arduino is ready. Pan: Pin 10, Tilt: Pin 9.");
}

void loop() {
  
  // Check if there is data available to read from the serial port
  if (Serial.available() > 0) {
    // Read the incoming data until a newline character is received
    // Python script sends data as "pan,tilt\n"
    serialData = Serial.readStringUntil('\n');

    // A command was received, so reset the timeout timer
    lastSerialTime = millis();
    
    // Find the comma that separates the pan and tilt values
    int commaIndex = serialData.indexOf(',');
    
    // Proceed only if a comma is found
    if (commaIndex > 0) {
      // Extract the pan and tilt angle strings
      String panString = serialData.substring(0, commaIndex);
      String tiltString = serialData.substring(commaIndex + 1);
      
      // Convert the strings to integers
      int panAngle = panString.toInt();
      int tiltAngle = tiltString.toInt();
      
      // Constrain the angles to the valid servo range (0-180) to be safe
      panAngle = constrain(panAngle, 0, 180);
      tiltAngle = constrain(tiltAngle, 0, 180);
      
      // Write the new angles to the servos
      panServo.write(panAngle);
      tiltServo.write(tiltAngle);
      
    }
  }

  // --- LED State Logic ---
  unsigned long currentTime = millis();

  // Check if we have lost the signal from the Python script
  if (currentTime - lastSerialTime > SEARCH_TIMEOUT) {
    bool searching_led_status;
    // --- SEARCHING STATE ---
    digitalWrite(LED_LOCKED_PIN, LOW); // Ensure locked LED is off

    // Blink the searching LED slowly
    if (currentTime - lastBlinkTime >= SEARCHING_BLINK_INTERVAL) {
      lastBlinkTime = currentTime;
      ledState = !ledState;
    }
    searching_led_status = ledState;
    digitalWrite(LED_SEARCHING_PIN, searching_led_status);
    digitalWrite(STATUS_OUTPUT_PIN, searching_led_status); // Mirror status to pin 5
  } else {
    bool locked_led_status = (currentTime / LOCKED_BLINK_INTERVAL) % 2;
    // --- SUCCESSFULLY TRACKED (LOCKED) STATE ---
    digitalWrite(LED_SEARCHING_PIN, LOW); // Ensure searching LED is off
    digitalWrite(LED_LOCKED_PIN, locked_led_status);
    digitalWrite(STATUS_OUTPUT_PIN, locked_led_status); // Mirror status to pin 5
  }
}
