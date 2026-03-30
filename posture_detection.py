import cv2
import mediapipe as mp
import numpy as np

class PostureDetector:
    def __init__(self):
        self.mp_holistic = mp.solutions.holistic
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Holistic model — pose + face + hands combined
        self.holistic = self.mp_holistic.Holistic(
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            model_complexity=1
        )

        # FaceMesh for precise head/eye tracking
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3
        )

        self.issues = []
        print("✅ PostureDetector initialized with Holistic + FaceMesh")

    def _get_coords(self, landmark):
        return [landmark.x, landmark.y]

    def _is_visible(self, landmark, threshold=0.4):
        return landmark.visibility > threshold

    def detect_posture(self, frame):
        h, w = frame.shape[:2]
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Run both models
        holistic_results  = self.holistic.process(image)
        facemesh_results  = self.face_mesh.process(image)

        image.flags.writeable = True
        display_frame = frame.copy()

        posture_status = "UNKNOWN"
        self.issues = []

        # ── DRAW holistic landmarks ──
        if holistic_results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                display_frame,
                holistic_results.pose_landmarks,
                self.mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 255, 0), thickness=2, circle_radius=3),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(0, 180, 255), thickness=2)
            )

        # ── DRAW face mesh landmarks ──
        if facemesh_results.multi_face_landmarks:
            for face_landmarks in facemesh_results.multi_face_landmarks:
                self.mp_drawing.draw_landmarks(
                    display_frame,
                    face_landmarks,
                    self.mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(255, 200, 0), thickness=1, circle_radius=1),
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(255, 200, 0), thickness=1)
                )

        # ── POSTURE CHECKS ──
        pose_lm = holistic_results.pose_landmarks

        if pose_lm is None:
            cv2.putText(display_frame, "Show upper body", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            return "UNKNOWN", display_frame

        lm = pose_lm.landmark
        PL = self.mp_holistic.PoseLandmark

        left_shoulder  = self._get_coords(lm[PL.LEFT_SHOULDER.value])
        right_shoulder = self._get_coords(lm[PL.RIGHT_SHOULDER.value])
        left_ear       = self._get_coords(lm[PL.LEFT_EAR.value])
        right_ear      = self._get_coords(lm[PL.RIGHT_EAR.value])

        avg_shoulder = [(left_shoulder[0]+right_shoulder[0])/2,
                        (left_shoulder[1]+right_shoulder[1])/2]
        avg_ear      = [(left_ear[0]+right_ear[0])/2,
                        (left_ear[1]+right_ear[1])/2]

        posture_status = "GOOD"

        # ── CHECK 1: Forward head lean (from Holistic) ──
        ear_x_diff = abs(avg_ear[0] - avg_shoulder[0])
        if ear_x_diff > 0.1:
            self.issues.append("Forward head lean")
            posture_status = "BAD"

        # ── CHECK 2: Head drooping down (from Holistic) ──
        if avg_ear[1] > avg_shoulder[1] - 0.03:
            self.issues.append("Head drooping down")
            posture_status = "BAD"

        # ── CHECK 3: Shoulder asymmetry (from Holistic) ──
        shoulder_tilt = abs(left_shoulder[1] - right_shoulder[1])
        if shoulder_tilt > 0.08:
            self.issues.append("Uneven shoulders")
            posture_status = "BAD"

        # ── CHECK 4: Eye strain / screen distance (from FaceMesh) ──
        if facemesh_results.multi_face_landmarks:
            face_lm = facemesh_results.multi_face_landmarks[0].landmark

            # Use eye landmarks to estimate distance
            # Landmark 33 = left eye outer, 263 = right eye outer
            left_eye  = face_lm[33]
            right_eye = face_lm[263]
            eye_distance = abs(left_eye.x - right_eye.x)

            # Also check head tilt using eye Y difference
            eye_tilt = abs(left_eye.y - right_eye.y)

            if eye_distance > 0.40:
                self.issues.append("Too close to screen")
                posture_status = "BAD"
            elif eye_distance < 0.12:
                self.issues.append("Too far from screen")
                posture_status = "BAD"

            if eye_tilt > 0.04:
                self.issues.append("Head tilted sideways")
                posture_status = "BAD"

            # Draw eye distance indicator on frame
            cv2.putText(display_frame,
                        f"Eye span: {eye_distance:.2f}",
                        (30, display_frame.shape[0] - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 0), 1)

        # ── DISPLAY status ──
        color = (0, 255, 0) if posture_status == "GOOD" else (0, 0, 255)
        cv2.putText(display_frame, f"Posture: {posture_status}",
                    (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)

        for i, issue in enumerate(self.issues):
            cv2.putText(display_frame, f"  {issue}",
                        (30, 95 + i * 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 165, 255), 2)

        return posture_status, display_frame

    def get_issues(self):
        return self.issues

    def __del__(self):
        self.holistic.close()
        self.face_mesh.close()
