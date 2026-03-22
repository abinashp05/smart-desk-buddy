
import cv2
import mediapipe as mp
import numpy as np

class PostureDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def _calculate_angle(self, a, b, c):
        a = np.array(a)  # First
        b = np.array(b)  # Mid
        c = np.array(c)  # End

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)

        if angle > 180.0:
            angle = 360 - angle
        return angle

    def detect_posture(self, frame):
        # Convert the image to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Make detection
        results = self.pose.process(image)

        # Convert back to BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        posture_status = "GOOD"
        display_frame = frame.copy()

        try:
            landmarks = results.pose_landmarks.landmark

            # Get coordinates for head/neck
            nose = [landmarks[self.mp_pose.PoseLandmark.NOSE.value].x, landmarks[self.mp_pose.PoseLandmark.NOSE.value].y]
            left_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            right_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            left_ear = [landmarks[self.mp_pose.PoseLandmark.LEFT_EAR.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_EAR.value].y]
            right_ear = [landmarks[self.mp_pose.PoseLandmark.RIGHT_EAR.value].x, landmarks[self.mp_pose.PoseLandmark.RIGHT_EAR.value].y]

            # Calculate average shoulder position
            shoulder_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
            avg_shoulder = [shoulder_x, shoulder_y]

            # Calculate average ear position
            ear_x = (left_ear[0] + right_ear[0]) / 2
            ear_y = (left_ear[1] + right_ear[1]) / 2
            avg_ear = [ear_x, ear_y]

            # Simple logic for posture detection
            # Check if head is too far forward (nose relative to shoulders)
            # A smaller x-coordinate for nose than shoulders indicates leaning forward
            if nose[0] < avg_shoulder[0] - 0.05: # Threshold can be adjusted
                posture_status = "BAD"
            # Check if head is too low (nose relative to shoulders)
            elif nose[1] > avg_shoulder[1] + 0.1: # Threshold can be adjusted
                posture_status = "BAD"
            # Check for slouching (ear relative to shoulder)
            elif avg_ear[1] > avg_shoulder[1] - 0.05: # If ears are too low compared to shoulders
                posture_status = "BAD"

            # Draw landmarks and connections (optional, for visualization)
            mp.solutions.drawing_utils.draw_landmarks(
                display_frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                mp.solutions.drawing_utils.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )

        except:
            pass # No pose detected

        return posture_status, display_frame

    def __del__(self):
        self.pose.close()
