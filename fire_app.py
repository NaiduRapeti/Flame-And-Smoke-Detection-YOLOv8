import os
import base64
import time
import logging
import threading
from io import BytesIO

from flask import Flask, render_template, request, jsonify, make_response
from ultralytics import YOLO
from PIL import Image
import numpy as np
import cv2

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")

# Initialize Flask app
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
            static_url_path='/static',
            template_folder='templates')

# App configuration
app.config.update(
    UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), UPLOAD_FOLDER),
    APPLICATION_ROOT='/',
    SEND_FILE_MAX_AGE_DEFAULT=0,  # Disable caching for development
    TEMPLATES_AUTO_RELOAD=True,
    PREFERRED_URL_SCHEME='http',
    SERVER_NAME=None
)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------- LOAD MODEL ----------------
model = YOLO(MODEL_PATH)

# Warm up the model with a dummy image to reduce first inference time
def warm_up_model():
    try:
        dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(dummy_image, verbose=False)
        logger.info("Model warmed up successfully")
    except Exception as e:
        logger.warning(f"Model warm-up failed: {e}")

# Warm up the model
warm_up_model()

# ---------------- ALARM STATE ----------------
alarm_active = False
alarm_thread = None
alarm_lock = threading.Lock()

# ---------------- HELPERS ----------------
def detect_and_annotate_bgr(bgr_image: np.ndarray):
    h, w = bgr_image.shape[:2]
    max_dim = 640
    scale = min(max_dim / h, max_dim / w)

    if scale < 1:
        bgr_image = cv2.resize(
            bgr_image,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_LINEAR
        )

    results = model.predict(
        source=bgr_image,
        conf=0.3,  
        iou=0.45,
        imgsz=640,
        max_det=10, 
        device="cpu",
        verbose=False
    )

    r = results[0]
    detections = []

    for box in r.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        label = model.names[cls]

        detections.append({
            "label": label,
            "confidence": conf,
            "box": [float(x1), float(y1), float(x2), float(y2)]
        })

    annotated = r.plot()
    return annotated, detections


def bgr_to_dataurl_png(bgr_img: np.ndarray) -> str:
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = BytesIO()
    pil.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

# ---------------- ALARM FUNCTIONS ----------------
def check_fire_or_smoke_detections(detections):
    """Check if fire or smoke is detected"""
    fire_smoke_labels = ['fire', 'smoke']
    for detection in detections:
        if detection['label'].lower() in fire_smoke_labels:
            return True
    return False

def start_alarm():
    """Start the alarm in a separate thread"""
    global alarm_active, alarm_thread
    
    with alarm_lock:
        if alarm_active:
            return
        
        alarm_active = True
        alarm_thread = threading.Thread(target=alarm_loop, daemon=True)
        alarm_thread.start()

def stop_alarm():
    """Stop the alarm"""
    global alarm_active
    with alarm_lock:
        alarm_active = False

def alarm_loop():
    """Alarm loop that runs in a separate thread"""
    # This creates a simple beep sound using system beep
    # In a real application, you might want to use a proper audio file
    import winsound  # Windows specific
    import platform
    
    while True:
        with alarm_lock:
            if not alarm_active:
                break
        
        try:
            if platform.system() == 'Windows':
                # Use Windows system beep
                winsound.Beep(1000, 500)  # Frequency: 1000Hz, Duration: 500ms
            else:
                # For non-Windows systems, print alarm message
                print("\a")  # Terminal bell
                time.sleep(0.5)
            
            time.sleep(0.5)  # Short pause between beeps
        except Exception as e:
            logger.error(f"Alarm sound error: {e}")
            time.sleep(1)

# ---------------- DEBUG ROUTES ----------------
@app.route('/debug/routes')
def debug_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return '<br>'.join(sorted(output))

@app.route('/debug/static')
def debug_static():
    import os
    static_files = []
    for root, dirs, files in os.walk('static'):
        for file in files:
            static_files.append(os.path.join(root, file))
    return '<br>'.join(static_files) if static_files else 'No static files found'

# ---------------- ROUTES ----------------

# HOME (matches base.html url_for('home'))
@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")


# ABOUT PAGE
@app.route("/about")
def about():
    return render_template("about.html")


# DETECT PAGE
@app.route("/detect")
def detect():
    return render_template("detect.html")


# IMAGE UPLOAD
@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response

    try:
        if 'images[]' not in request.files:
            return jsonify({"error": "No files provided"}), 400
            
        files = request.files.getlist("images[]")
        if not files or len(files) == 0:
            return jsonify({"error": "No files selected"}), 400

        uploaded = []
        detections = []

        for f in files:
            if not f or f.filename == '':
                continue
                
            # Create a secure filename
            filename = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
            
            # Save the file
            f.save(filename)
            
            # Read the image
            try:
                bgr = cv2.imdecode(np.fromfile(filename, np.uint8), cv2.IMREAD_COLOR)
                if bgr is None:
                    pil = Image.open(filename).convert("RGB")
                    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                
                # Process the image
                annotated, detection_results = detect_and_annotate_bgr(bgr)
                
                # Check for fire or smoke and trigger alarm if detected
                if check_fire_or_smoke_detections(detection_results):
                    start_alarm()
                    logger.warning("Fire or smoke detected in uploaded image! Alarm triggered.")
                else:
                    stop_alarm()
                    logger.info("No fire or smoke detected in uploaded image. Alarm stopped.")
                
                # Convert to data URLs
                uploaded.append(bgr_to_dataurl_png(bgr))
                detections.append(bgr_to_dataurl_png(annotated))
                
            except Exception as e:
                logger.error(f"Error processing file {f.filename}: {str(e)}")
                continue

        if not uploaded or not detections:
            return jsonify({"error": "Failed to process any images"}), 500

        response = jsonify({
            "status": "success",
            "uploaded": uploaded,
            "detections": detections
        })
        
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
        
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


# CAMERA CAPTURE
@app.route("/capture", methods=["POST", "OPTIONS"])
def capture():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response

    # Set CORS headers for the main response
    response_headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }

    try:
        # Check if the request has the file part
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400, response_headers

        file = request.files["image"]
        
        # Check if file is empty
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400, response_headers
            
        # Check file size (limit to 10MB)
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > 10 * 1024 * 1024:  # 10MB limit
            return jsonify({"error": "File size exceeds 10MB limit"}), 400, response_headers

        try:
            # Read and validate image
            file_bytes = file.read()
            if not file_bytes:
                return jsonify({"error": "Empty file content"}), 400, response_headers
                
            file_np = np.frombuffer(file_bytes, np.uint8)
            bgr = cv2.imdecode(file_np, cv2.IMREAD_COLOR)

            if bgr is None:
                return jsonify({"error": "Invalid or unsupported image format"}), 400, response_headers

            # Process the image
            try:
                start = time.time()
                annotated, detections = detect_and_annotate_bgr(bgr)
                process_time = time.time() - start
                
                # Check for fire or smoke and trigger alarm if detected
                if check_fire_or_smoke_detections(detections):
                    start_alarm()
                    logger.warning("Fire or smoke detected! Alarm triggered.")
                else:
                    stop_alarm()
                    logger.info("No fire or smoke detected. Alarm stopped.")

                response_data = {
                    "status": "success",
                    "annotated_image": bgr_to_dataurl_png(annotated),
                    "detections": detections,
                    "process_time": round(process_time, 2),
                    "detection_count": len(detections),
                    "alarm_active": alarm_active
                }
                
                logger.info(f"Successfully processed image. Detections: {len(detections)}")
                return jsonify(response_data), 200, response_headers
                
            except Exception as proc_error:
                logger.error(f"Error in image processing: {str(proc_error)}", exc_info=True)
                return jsonify({"error": "Error processing image"}), 500, response_headers
            
        except Exception as validation_error:
            logger.error(f"Image validation error: {str(validation_error)}", exc_info=True)
            return jsonify({"error": "Invalid image data"}), 400, response_headers
            
    except Exception as e:
        logger.error(f"Unexpected error in /capture: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500, response_headers


# ALARM CONTROL ENDPOINT
@app.route("/alarm", methods=["POST", "OPTIONS"])
def alarm_control():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response

    response_headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }

    try:
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({"error": "Missing action parameter"}), 400, response_headers

        action = data['action']
        
        if action == 'stop':
            stop_alarm()
            logger.info("Alarm manually stopped by user")
            return jsonify({
                "status": "success",
                "message": "Alarm stopped",
                "alarm_active": False
            }), 200, response_headers
        elif action == 'status':
            return jsonify({
                "status": "success",
                "alarm_active": alarm_active
            }), 200, response_headers
        else:
            return jsonify({"error": "Invalid action"}), 400, response_headers
            
    except Exception as e:
        logger.error(f"Error in alarm control: {str(e)}")
        return jsonify({"error": str(e)}), 500, response_headers


# Health check endpoint
@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    try:
        # Add any additional health checks here
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'model_loaded': model is not None
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ---------------- RUN ----------------
if __name__ == "__main__":
    # Ensure templates are auto-reloaded
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=5000)
