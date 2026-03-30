from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import threading
import time
import serial
from posture_detection import PostureDetector
from voice_assistant import VoiceAssistant

# ── SERIAL CONNECTION (safe) ──
esp = None
try:
    esp = serial.Serial("COM3", 115200)
    time.sleep(2)
    esp.flush()
    print("✅ ESP32 connected on COM3")
except serial.SerialException:
    print("⚠️  ESP32 not connected. Running in software-only mode.")

app = Flask(__name__)
CORS(app)

# ── GLOBALS ──
posture_detector   = PostureDetector()
voice_assistant    = VoiceAssistant()        # NEW
video_capture      = None
output_frame       = None
lock               = threading.Lock()

current_posture_status = "UNKNOWN"
current_issues         = []
current_system_message = "Initializing..."


# ── SERIAL ALERT ──
def send_alert_to_esp32(status):
    if esp is None:
        print(f"[No ESP32] Would send: {status}")
        return
    try:
        esp.write((status + "\n").encode())
        print(f"Sent to ESP32: {status}")
    except Exception as e:
        print(f"Serial error: {e}")


# ── VIDEO STREAM GENERATOR ──
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


# ── POSTURE DETECTION THREAD ──
def detect_posture_from_webcam():
    global video_capture, output_frame
    global current_posture_status, current_issues, current_system_message

    bad_start_time  = None
    alarm_active    = False
    was_bad_before  = False   # track previous state for "corrected" voice

    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("❌ Error: Could not open webcam.")
        current_system_message = "Webcam Error"
        return

    current_system_message = "Monitoring Active"
    voice_assistant.speak("Smart Desk Buddy is now active. Sit comfortably and I will monitor your posture.")
    print("📷 Webcam started")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Frame read error")
            break

        frame = cv2.flip(frame, 1)

        posture, display_frame = posture_detector.detect_posture(frame)
        issues = posture_detector.get_issues()

        # ── BAD posture timer → ESP32 + Voice ──
        if posture == "BAD":
            if bad_start_time is None:
                bad_start_time = time.time()

            bad_duration = time.time() - bad_start_time

            # After 3 seconds of bad posture → alert
            if bad_duration >= 3 and not alarm_active:
                print("⚠️  Bad posture for 3 seconds!")
                send_alert_to_esp32("START")
                voice_assistant.alert_bad_posture(issues)   # 🔊 VOICE ALERT
                alarm_active   = True
                was_bad_before = True

        else:
            bad_start_time = None
            if alarm_active:
                print("✅ Posture corrected!")
                send_alert_to_esp32("STOP")
                if was_bad_before:
                    voice_assistant.alert_posture_corrected()  # 🔊 VOICE CORRECTED
                alarm_active   = False
                was_bad_before = False

        # Update globals
        current_posture_status = posture
        current_issues         = issues

        with lock:
            output_frame = display_frame.copy()

        time.sleep(0.05)

    video_capture.release()


# ── ROUTES ──
@app.route("/")
def home():
    return send_from_directory(".", "dashboard.html")

@app.route("/dashboard.html")
def dashboard_file():
    return send_from_directory(".", "dashboard.html")

@app.route("/styles.css")
def styles():
    return send_from_directory(".", "styles.css")

@app.route("/script.js")
def script():
    return send_from_directory(".", "script.js")

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
        "system": current_system_message,
        "issues": current_issues
    })


# ── MAIN ──
if __name__ == "__main__":
    posture_thread = threading.Thread(target=detect_posture_from_webcam)
    posture_thread.daemon = True
    posture_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
