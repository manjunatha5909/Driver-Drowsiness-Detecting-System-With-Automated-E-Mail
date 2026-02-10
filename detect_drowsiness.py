# detect_drowsiness.py
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import simpleaudio as sa
import os
from math import hypot

from email_alert import send_email_alert

# === CONFIGURABLE PARAMETERS ===
EAR_THRESHOLD = 0.25       # EAR below this value => eye considered closed
CONSECUTIVE_FRAMES = 20   # number of frames EAR must be below threshold to trigger
ALARM_SOUND = "alarm.mp3" # path to alarm sound (provide your own mp3/wav in the folder)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_USER = "emaail"          # change
EMAIL_APP_PASSWORD = "pasward"     # change - use app password for Gmail
ALERT_RECIPIENTS = ["receiver mail"] # change
SEND_ONCE_PER_EVENT = True  # if True, send one email per drowsiness event until eyes reopen
SNAPSHOT_FOLDER = "snapshots"
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,
                                  max_num_faces=1,
                                  refine_landmarks=True,
                                  min_detection_confidence=0.5,
                                  min_tracking_confidence=0.5)

# Landmark indices for MediaPipe face mesh (eyes)
# Right eye (from camera view): [33, 160, 158, 133, 153, 144]
# Left eye (from camera view):  [362, 385, 387, 263, 373, 380]
R_EYE = [33, 160, 158, 133, 153, 144]
L_EYE = [362, 385, 387, 263, 373, 380]

def eye_aspect_ratio(landmarks, eye_indices, image_w, image_h):
    # landmarks are normalized; convert to pixel coords
    coords = []
    for idx in eye_indices:
        lm = landmarks[idx]
        coords.append((int(lm.x * image_w), int(lm.y * image_h)))
    # p1..p6
    p1, p2, p3, p4, p5, p6 = coords
    # vertical distances
    v1 = hypot(p2[0]-p6[0], p2[1]-p6[1])
    v2 = hypot(p3[0]-p5[0], p3[1]-p5[1])
    # horizontal distance
    h = hypot(p1[0]-p4[0], p1[1]-p4[1])
    if h == 0:
        return 0
    ear = (v1 + v2) / (2.0 * h)
    return ear, coords

def play_alarm_thread(sound_path):
    try:
        wave_obj = sa.WaveObject.from_wave_file(sound_path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print("Could not play sound:", e)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    counter = 0
    alarm_on = False
    email_sent_for_event = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(img_rgb)

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0].landmark
            h, w = frame.shape[:2]
            ear_r, coords_r = eye_aspect_ratio(face_landmarks, R_EYE, w, h)
            ear_l, coords_l = eye_aspect_ratio(face_landmarks, L_EYE, w, h)
            ear = (ear_r + ear_l) / 2.0

            # draw eye contours
            for (x, y) in coords_r + coords_l:
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

            cv2.putText(frame, f"EAR: {ear:.3f}", (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            if ear < EAR_THRESHOLD:
                counter += 1
                # print debug
                # print("EAR low:", ear, "counter:", counter)
                if counter >= CONSECUTIVE_FRAMES:
                    if not alarm_on:
                        alarm_on = True
                        # Start alarm in separate thread (non-blocking)
                        if os.path.exists(ALARM_SOUND):
                            t = threading.Thread(target=play_alarm_thread, args=(ALARM_SOUND,), daemon=True)
                            t.start()
                        else:
                            print("Alarm sound file not found:", ALARM_SOUND)
                    cv2.putText(frame, "DROWSINESS ALERT!", (30, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

                    # save snapshot
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    snapshot_path = os.path.join(SNAPSHOT_FOLDER, f"drowsy_{timestamp}.jpg")
                    cv2.imwrite(snapshot_path, frame)

                    # Send email alert (only once per event)
                    if not email_sent_for_event:
                        try:
                            subject = "Driver Drowsiness Alert"
                            body = f"Drowsiness detected at {time.strftime('%Y-%m-%d %H:%M:%S')}. See attached snapshot."
                            send_email_alert(SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_APP_PASSWORD,
                                             subject, body, ALERT_RECIPIENTS, attachment_path=snapshot_path)
                            print("Email alert sent.")
                        except Exception as e:
                            print("Failed to send email:", e)
                        email_sent_for_event = True

            else:
                # reset counters and flags when eyes open again
                counter = 0
                alarm_on = False
                email_sent_for_event = False

        # show frame
        cv2.imshow("Driver Drowsiness Detection", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC to quit
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
