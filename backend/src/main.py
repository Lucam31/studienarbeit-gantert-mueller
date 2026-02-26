from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from picamera2 import Picamera2
import os
import subprocess

app = FastAPI(title="PiCam V3 API")

# CORS Setup: Erlaubt deinem React-Frontend den Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kamera-Initialisierung (Singleton-Style)
picam2 = Picamera2()
config = picam2.create_video_configuration()
picam2.configure(config)
picam2.start()

@app.get("/stream")
async def video_stream():
    """MJPEG Video Stream Endpunkt"""
    def generate():
        while True:
            frame = picam2.capture_file(format='jpeg', output_type='bytes')
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/status")
async def get_status():
    """Gibt die CPU Temperatur zurück"""
    temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
    temp = temp_output.replace("temp=", "").replace("'C\n", "")
    return {"temp": temp, "camera": "online"}

@app.post("/focus")
async def trigger_focus():
    """Löst den Autofokus der Cam V3 aus"""
    picam2.autofocus_cycle()
    return {"status": "focused"}