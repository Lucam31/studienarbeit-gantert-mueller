import cv2
import numpy as np
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
        self.process_interval_s = 0.2
        self.last_error = 0.0
        self.Kp = 0.15
        self.Kd = 0.1
        self.base_speed = 0.1  # 10%

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
        error_count = 0
        last_process_time = 0.0
        
        while self._running:
            grabbed = cap.grab()
            if not grabbed:
                error_count += 1
                self.status.emit(f"Vision: Fehler beim Frame-Grabbing ({error_count})")
                print(f"[VISION ERROR] Failed to grab frame (error_count={error_count})")
                if error_count > 10:
                    break
                time.sleep(0.05)
                continue

            error_count = 0

            now = time.monotonic()
            if now - last_process_time < self.process_interval_s:
                time.sleep(0.01)
                continue

            ret, frame = cap.retrieve()
            if not ret:
                error_count += 1
                self.status.emit(f"Vision: Fehler beim Frame-Retrieval ({error_count})")
                print(f"[VISION ERROR] Failed to retrieve frame (error_count={error_count})")
                if error_count > 10:
                    break
                time.sleep(0.05)
                continue

            last_process_time = now

            processed, error, confidence = self.process_frame(frame)

            if confidence > 0.0:
                derivative = error - self.last_error
                correction  = self.Kp * error + self.Kd * derivative
                self.last_error = error
                
                # In Joystick-Format umrechnen
                x = correction / 100.0   # Lenkung: -1.0 (links) bis 1.0 (rechts)
                y = self.base_speed       # Vorwärtsgeschwindigkeit: fix z.B. 0.5
            else:
                x = 0.0
                y = 0.0
                self.last_error = 0.0

            self.steeringCommand.emit(x*100, y*100)

            if self.mjpeg_server is not None:
                try:
                    ret_enc, jpeg = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret_enc:
                        self.mjpeg_server.put_frame(jpeg.tobytes())
                except Exception as e:
                    print(f"[VISION ERROR] Failed to encode/send frame: {e}")
            
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
        
        # Frame auf untere 50% beschränken
        height, width = frame.shape[:2]
        roi_frame = frame[height // 2:, :]
        
        # in hsv konvertieren 
        # Farbton, Sättigung, Helligkeit
        hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        
        # Maske fuer orange Farbe erstellen (hoehere Saettigung, damit weiss nicht triggert)
        lower = np.array([0, 130, 60])
        upper = np.array([30, 255, 255])

        mask = cv2.inRange(hsv, lower, upper)
                # Rauschen entfernen und kleine Luecken schliessen
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        
        # Loecher in der Maske fuellen (z.B. durch Ueberbelichtung)
        flood = mask.copy()
        cv2.floodFill(flood, None, (0, 0), 255)
        flood_inv = cv2.bitwise_not(flood)
        mask = cv2.bitwise_or(mask, flood_inv)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            
            if cv2.contourArea(largest) > 100:
                # Centroid für Steuerung
                M = cv2.moments(largest)
                cx = int(M["m10"] / M["m00"])
                
                # Fehler relativ zur Bildmitte
                error = cx - (width // 2)
                
                # Kontur einzeichnen (auf roi_frame, nicht frame)
                cv2.drawContours(roi_frame, [largest], -1, (0, 255, 0), 2)
                cv2.circle(roi_frame, (cx, int(M["m01"] / M["m00"])), 5, (0, 0, 255), -1)
                return roi_frame, error / (width // 2) * 100, 10.0

        print("[VISION] Frame processed")
        return roi_frame, 0.0, 0.0
        

    @Slot()
    def stop_processing(self):
        print("[VISION] Stopping...")
        self._running = False
