from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import threading
import time
import serial
from posture_detection import PostureDetector
from voice_assistant import VoiceAssistant

# ── SERIAL CONNECTION ──
esp = None
try:
    esp = serial.Serial("COM3", 115200)
    time.sleep(2)
    esp.flush()
    print("✅ ESP32 connected on COM3")
except:
    print("⚠️ ESP32 not connected. Running in software-only mode.")

app = Flask(__name__)
CORS(app)

# ── GLOBALS ──
posture_detector = PostureDetector()
voice_assistant = VoiceAssistant()

video_capture = None
output_frame = None
lock = threading.Lock()

current_posture_status = "UNKNOWN"
current_issues = []
current_system_message = "Initializing..."

# ── SERIAL SEND FUNCTION ──
def send_alert_to_esp32(status):
    if esp is None:
        print(f"[No ESP32] Would send: {status}")
        return
    try:
        esp.write((status + "\n").encode())
        print(f"📤 Sent to ESP32: {status}")
    except Exception as e:
        print(f"Serial error: {e}")

# ── VIDEO STREAM ──
def generate_frames():
    while True:
        with lock:
            if output_frame is None:
                continue
            flag, encoded = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
            frame_bytes = bytearray(encoded)

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

# ── POSTURE DETECTION ──
def detect_posture_from_webcam():
    global video_capture, output_frame
    global current_posture_status, current_issues, current_system_message

    bad_start_time = None
    alarm_active = False
    was_bad_before = False
    prev_status = ""   # 🔥 IMPORTANT

    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("❌ Webcam error")
        return

    print("📷 Webcam started")
    voice_assistant.speak("Smart Desk Buddy is now active.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        posture, display_frame = posture_detector.detect_posture(frame)
        issues = posture_detector.get_issues()

        # ── BAD POSTURE LOGIC ──
        if posture == "BAD":
            if bad_start_time is None:
                bad_start_time = time.time()

            bad_duration = time.time() - bad_start_time

            if bad_duration >= 3:
                alarm_active = True
                was_bad_before = True

        else:
            bad_start_time = None
            alarm_active = False

        # ── SEND TO ESP32 (ONLY WHEN CHANGED) ──
        # ── SEND TO ESP32 (CONTINUOUS) ──
if alarm_active:
    status = "BAD"
else:
    status = "GOOD"

send_alert_to_esp32(status)   # 🔥 ALWAYS SEND

print("Sending:", status)     # (for debugging)

# voice logic
if status == "BAD":
    voice_assistant.alert_bad_posture(issues)
else:
    if was_bad_before:
        voice_assistant.alert_posture_corrected()
        was_bad_before = False

prev_status = status

        # Update globals
        current_posture_status = posture
        current_issues = issues

        with lock:
            output_frame = display_frame.copy()

        time.sleep(0.05)

    video_capture.release()

# ── ROUTES ──
@app.route("/")
def home():
    return send_from_directory(".", "dashboard.html")

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/status")
def get_status():
    return jsonify({
        "status": current_posture_status,
        "issues": current_issues,
        "system": current_system_message
    })

# ── MAIN ──
if __name__ == "__main__":
    t = threading.Thread(target=detect_posture_from_webcam)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
