import cv2
import threading
import time
from PySide6.QtCore import QObject, Signal, Slot

class VisionWorker(QObject):
    steeringCommand = Signal(float, float)  # x, y für Joystick-Steuerung
    status = Signal(str)
    finished = Signal()

    def __init__(self, rtsp_url: str = "rtsp://127.0.0.1:8554/cam", mjpeg_server=None):
        super().__init__()
        self._running = False
        self.rtsp_url = rtsp_url
        self.mjpeg_server = mjpeg_server  # MJPEGServer-Instanz

    @Slot()
    def start_processing(self):
        if self._running:
            return
        
        self._running = True
        self.status.emit(f"Vision: Verbinde zu RTSP-Stream ({self.rtsp_url})...")
        print(f"[VISION] Starting RTSP connection to {self.rtsp_url}")
        
        # RTSP-Stream mit Timeout öffnen
        cap = cv2.VideoCapture(self.rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimaler Buffer für niedrige Latenz
        
        if not cap.isOpened():
            msg = f"Vision: Konnte Stream nicht öffnen: {self.rtsp_url}"
            self.status.emit(msg)
            print(f"[VISION ERROR] {msg}")
            self._running = False
            self.finished.emit()
            return
        
        self.status.emit("Vision: Stream geöffnet, verarbeite Frames...")
        print("[VISION] RTSP Stream opened successfully")
        frame_count = 0
        error_count = 0
        
        while self._running:
            ret, frame = cap.read()
            if not ret:
                error_count += 1
                self.status.emit(f"Vision: Fehler beim Frame-Lesen ({error_count})")
                print(f"[VISION ERROR] Failed to read frame (error_count={error_count})")
                if error_count > 10:
                    break
                time.sleep(0.1)
                continue
            
            error_count = 0  # Reset error count on successful read
            
            # --- DEINE BILDVERARBEITUNG HIER ---
            # Beispiel: Linienerkennung
            x, y = self.process_frame(frame)
            self.steeringCommand.emit(float(x), float(y))
            
            # Debug-Frame in MJPEG-Stream schreiben
            if self.mjpeg_server is not None:
                try:
                    ret_enc, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret_enc:
                        self.mjpeg_server.put_frame(jpeg.tobytes())
                        if frame_count % 50 == 0:
                            print(f"[VISION] Sent frame {frame_count} to MJPEG server (size: {len(jpeg.tobytes())} bytes)")
                except Exception as e:
                    print(f"[VISION ERROR] Failed to encode/send frame: {e}")
            
            frame_count += 1
            if frame_count % 100 == 0:
                self.status.emit(f"Vision: {frame_count} Frames verarbeitet")
            
        cap.release()
        self._running = False
        self.status.emit("Vision: gestoppt")
        print("[VISION] Stopped")
        self.finished.emit()

    def process_frame(self, frame) -> tuple:
        """
        Verarbeite Frame und gebe Steuerwerte zurück.
        Returns: (x, y) wobei beide in [-100, 100]
        """
        # TODO: Hier deine echte Vision-Pipeline
        # Beispiel: Linien-Tracking, Objekt-Erkennung, etc.
        return 0.0, 0.0

    @Slot()
    def stop_processing(self):
        print("[VISION] Stopping...")
        self._running = False
