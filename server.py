from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import threading
import time
import serial
from posture_detection import PostureDetector


# SERIAL CONNECTION TO ESP32
esp = serial.Serial("COM3", 115200)
time.sleep(2)
esp.flush()

app = Flask(__name__)
CORS(app)

# Global variables
posture_detector = PostureDetector()
video_capture = None
output_frame = None
lock = threading.Lock()
current_posture_status = "UNKNOWN"


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


def generate_frames():
    global output_frame

    while True:
        with lock:
            if output_frame is None:
                continue

            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)

            if not flag:
                continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + bytearray(encodedImage)
            + b"\r\n"
        )


def send_alert_to_esp32(status):
    try:
        esp.write((status + "\n").encode())
        print("Sent to ESP32:", status)
    except Exception as e:
        print("Serial error:", e)


def detect_posture_from_webcam():

    global video_capture
    global output_frame
    global current_posture_status

    bad_start_time = None
    alarm_active = False

    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:

        ret, frame = video_capture.read()

        if not ret:
            print("Frame read error")
            break

        frame = cv2.flip(frame, 1)

        posture, display_frame = posture_detector.detect_posture(frame)

        # -------- BAD posture timer --------

        if posture == "BAD":

            if bad_start_time is None:
                bad_start_time = time.time()

            bad_duration = time.time() - bad_start_time

            if bad_duration >= 3 and not alarm_active:

                print("Bad posture for 3 seconds")

                send_alert_to_esp32("START")

                alarm_active = True

        else:

            bad_start_time = None

            if alarm_active:

                print("Posture corrected")

                send_alert_to_esp32("STOP")

                alarm_active = False

        current_posture_status = posture

        # -------- Display text on video --------

        color = (0, 255, 0) if posture == "GOOD" else (0, 0, 255)

        cv2.putText(
            display_frame,
            f"Posture: {posture}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display_frame,
            "System: Monitoring Active",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        with lock:
            output_frame = display_frame.copy()

        time.sleep(0.05)

    video_capture.release()


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
        "system": "Monitoring Active"
    })


if __name__ == "__main__":

    posture_thread = threading.Thread(target=detect_posture_from_webcam)
    posture_thread.daemon = True
    posture_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=False)