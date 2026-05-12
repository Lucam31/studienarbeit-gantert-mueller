import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue

class MJPEGHandler(BaseHTTPRequestHandler):
    """HTTP Handler für MJPEG-Stream"""
    
    def do_GET(self):
        if self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.send_header('Connection', 'close')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            timeout_count = 0
            while True:
                try:
                    jpeg_data = self.server.frame_buffer.get(timeout=1)
                    timeout_count = 0
                    
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(jpeg_data)}\r\n\r\n'.encode())
                    self.wfile.write(jpeg_data)
                    self.wfile.write(b'\r\n')
                except Exception as e:
                    timeout_count += 1
                    if timeout_count > 5:  # Nach 5 Timeouts die Verbindung beenden
                        break
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Supprimiere Logs"""
        pass

class MJPEGServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.frame_buffer = Queue(maxsize=2)
        self.server = None
        self.thread = None
        self._running = False

    def start(self):
        if self._running:
            return
        
        self._running = True
        self.server = HTTPServer(('0.0.0.0', self.port), MJPEGHandler)
        self.server.frame_buffer = self.frame_buffer
        self.server.timeout = 1
        
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        print(f"MJPEG-Server gestartet auf http://0.0.0.0:{self.port}/stream")

    def _run_server(self):
        while self._running:
            try:
                self.server.handle_request()
            except Exception as e:
                print(f"MJPEG-Server Error: {e}")

    def stop(self):
        self._running = False
        if self.server:
            try:
                self.server.server_close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=1)
        print("MJPEG-Server gestoppt.")

    def put_frame(self, jpeg_data: bytes):
        """Neuen Frame in den Stream schreiben"""
        try:
            self.frame_buffer.put_nowait(jpeg_data)
        except:
            pass  # Buffer voll, Frame überspringen
