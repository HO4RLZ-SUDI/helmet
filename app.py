# ===============================
# Helmet AI Detection Server
# Production-ready Flask version
# ===============================

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime, date
import threading
import os

# ===============================
# APP SETUP
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)


CORS(app)

# จำกัดขนาดไฟล์ (กัน DoS)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB


# ===============================
# LOAD MODEL (โหลดครั้งเดียว)
# ===============================

MODEL_PATH = "helmet.pt"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("❌ helmet.pt not found in project folder")

print("🔄 Loading YOLO model...")
model = YOLO(MODEL_PATH)
print("✅ Model loaded!")


# ===============================
# GLOBAL STATE (thread-safe)
# ===============================

lock = threading.Lock()
today_count = 0
current_date = date.today().isoformat()


# ===============================
# ROUTES
# ===============================

@app.route("/")
def index():
    # ใช้ render_template เท่านั้น (ห้าม send_from_directory)
    return render_template("index.html")


# -------------------------------
# DETECTION API
# -------------------------------

@app.route("/detect", methods=["POST"])
def detect():
    global today_count, current_date

    if "image" not in request.files:
        return "No image uploaded", 400

    file = request.files["image"]

    try:
        img = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(img, cv2.IMREAD_COLOR)

        if frame is None:
            return "Invalid image", 400

    except Exception:
        return "Image decode failed", 400

    # -------- YOLO inference --------
    try:
        results = model(frame, conf=0.4)
    except Exception:
        return "Model inference error", 500

    no_helmet = 0

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]

            if label.lower() in ["no helmet", "without helmet", "no-helmet"]:
                no_helmet += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(
                    frame,
                    "NO HELMET",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

    # -------- reset count per day --------
    today = date.today().isoformat()

    with lock:
        if today != current_date:
            today_count = 0
            current_date = today

        today_count += no_helmet

    # -------- return processed image --------
    _, jpg = cv2.imencode(".jpg", frame)

    return jpg.tobytes(), 200, {
        "Content-Type": "image/jpeg"
    }


# -------------------------------
# STATS API
# -------------------------------

@app.route("/stats")
def stats():
    return jsonify({
        "date": current_date,
        "no_helmet": today_count,
        "time": datetime.now().strftime("%H:%M:%S")
    })


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    print("\n🚀 Helmet AI Server Started")
    print("🌐 http://localhost:5000\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,   # ห้ามเปิด production
        threaded=True
    )
