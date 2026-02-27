from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from PySide6.QtCore import QObject, Signal, QTimer, QCoreApplication
from websocket.server import WebSocket
import json
from utils.logger import Logger
try:
    from picamera2 import Picamera2
except:
    print("Picamera2 library not found. Please install it to use the camera features.")
import os
import subprocess
import signal

class MainApp(QObject):
    def __init__(self):
        super().__init__()
        self.websocket = WebSocket()
        self.websocket.SignalMessageReceived.connect(self.handle_websocket_message)

    def handle_websocket_message(self, message):
        print(f"Message received from WebSocket: {message}")
        # Hier kannst du die Logik implementieren, um auf die empfangenen Nachrichten zu reagieren

    def handle_close_event(self, signal_received, frame):
        print("\nCtrl+C detected. Closing application...")
        self.websocket.stop_server()
        app.quit()

# app = FastAPI(title="PiCam V3 API")

# # CORS Setup: Erlaubt deinem React-Frontend den Zugriff
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], 
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Kamera-Initialisierung (Singleton-Style)
# picam2 = Picamera2()
# config = picam2.create_video_configuration()
# picam2.configure(config)
# picam2.start()

# @app.get("/stream")
# async def video_stream():
#     """MJPEG Video Stream Endpunkt"""
#     def generate():
#         while True:
#             frame = picam2.capture_file(format='jpeg', output_type='bytes')
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
#     return Response(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

# @app.get("/status")
# async def get_status():
#     """Gibt die CPU Temperatur zurück"""
#     temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
#     temp = temp_output.replace("temp=", "").replace("'C\n", "")
#     return {"temp": temp, "camera": "online"}

# @app.post("/focus")
# async def trigger_focus():
#     """Löst den Autofokus der Cam V3 aus"""
#     picam2.autofocus_cycle()
#     return {"status": "focused"}

if __name__ == "__main__":
    app = QCoreApplication([])
    main_app = MainApp()
    main_app.websocket.start_server(50000)

    signal.signal(signal.SIGINT, main_app.handle_close_event)

    app.exec()