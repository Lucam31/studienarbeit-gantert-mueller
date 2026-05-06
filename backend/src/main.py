import time

from PySide6.QtCore import QObject, QTimer, QCoreApplication, QThread
from websocket.server import WebSocket
import signal, json

import hardware.controller as controller
import hardware.drivers as drivers
from vision.worker import VisionWorker
from vision.mjpeg_server import MJPEGServer

class MainApp(QObject):
    def __init__(self):
        super().__init__()
        self.drivers = drivers.Drivers()
        self.controller = controller.Controller(self.drivers)
        self.emergency_stop_active = False
        self.vision_thread = None
        self.vision_worker = None
        
        # MJPEG-Server für Debug-Stream
        self.mjpeg_server = MJPEGServer(port=8080)
        self.mjpeg_server.start()
        
        self.websocket = WebSocket()
        self.websocket.SignalMessageReceived.connect(self.handle_websocket_message)
        self.websocket.start_server(50000)
        self.control_timer = QTimer(self)
        self.control_timer.timeout.connect(self.controller.update)
        self.control_timer.start(20)
        timer = QTimer(self)
        timer.timeout.connect(self.emergency_stop)
        timer.start(500)  # Call emergency_stop every 500 ms

    ## Callback function to handle messages received from the WebSocket server
    # @param msg_id: The ID of the message received from the client
    # @param payload: The payload of the message received from the client
    # @description: This function is called when a message is received from the WebSocket server. It processes the message and implements the logic to handle different types of messages based on their IDs.
    def handle_websocket_message(self, msg_id: str, payload: str) -> None:
        # implement logic for handling messages from the WebSocket
        """ differenciate between message ids? one id for drive command, one for follow the line command, etc. """
        msg_id = json.loads(msg_id)
        payload = json.loads(payload)
        
        if msg_id in ("drive_command", "joystick_command"):
            # Joystick payload (preferred): x/y in [-100, 100]
            # - y controls throttle (forward/back)
            # - x controls steering (left/right)
            if "x" in payload and "y" in payload:
                self.controller.drive_joystick(x=payload["x"], y=payload["y"])
                return
            else:
                print("Joystick command missing 'x' or 'y' in payload")

            # Legacy payload: speed + steering
            # speed: typically [-100, 100]
            # steering: either [-1, 1] or [-100, 100]
            #speed = float(payload.get("speed", 0))
            #steering_raw = float(payload.get("steering", 0))

            #steering = steering_raw / 100.0 if abs(steering_raw) > 1.0 else steering_raw
            #if steering < -1.0:
            #    steering = -1.0
            #if steering > 1.0:
            #    steering = 1.0

            #if speed > 0:
            #    self.controller.drive(speed, steering, True)
            #elif speed < 0:
            #    self.controller.drive(-speed, steering, False)
            #else:
            #    self.controller.stop()
        elif msg_id == "follow_line_command":
            action = str(payload.get("action", "")).lower()
            enabled = payload.get("enabled")

            if action == "start" or enabled is True:
                self.start_vision_worker()
            elif action == "stop" or enabled is False:
                self.stop_vision_worker()
            else:
                print(
                    "follow_line_command needs payload.action=start|stop "
                    "or payload.enabled=true|false"
                )
        else:
            print(f"Unknown message id: {msg_id}")

    def start_vision_worker(self) -> None:
        if self.vision_thread is not None and self.vision_thread.isRunning():
            print("Vision worker is already running.")
            return

        self.vision_thread = QThread(self)
        self.vision_worker = VisionWorker(
            rtsp_url="rtsp://127.0.0.1:8554/cam",
            mjpeg_server=self.mjpeg_server
        )
        self.vision_worker.moveToThread(self.vision_thread)

        self.vision_thread.started.connect(self.vision_worker.start_processing)
        self.vision_worker.steeringCommand.connect(self.on_vision_command)
        self.vision_worker.status.connect(print)
        self.vision_worker.finished.connect(self.vision_thread.quit)
        self.vision_worker.finished.connect(self.vision_worker.deleteLater)
        self.vision_thread.finished.connect(self._on_vision_thread_finished)

        self.vision_thread.start()
        print("Vision worker thread started.")

    def stop_vision_worker(self) -> None:
        if self.vision_worker is not None:
            self.vision_worker.stop_processing()

        if self.vision_thread is not None and self.vision_thread.isRunning():
            self.vision_thread.quit()
            self.vision_thread.wait(3000)
            print("Vision worker thread stopped.")

    def _on_vision_thread_finished(self) -> None:
        if self.vision_thread is not None:
            self.vision_thread.deleteLater()
        self.vision_thread = None
        self.vision_worker = None

    def on_vision_command(self, x: float, y: float) -> None:
        """Callback wenn Vision-Worker einen Steuerbefehl sendet"""
        self.controller.drive_joystick(x=x, y=y)

    ## Callback function to handle close event (e.g., when Ctrl+C is pressed)
    # @param signal_received: The signal received (e.g., SIGINT)
    # @param frame: The current stack frame (not used in this function)
    # @description: This function is called when a close event is triggered (e.g., when Ctrl+C is pressed in the console). It performs cleanup operations, such as stopping the WebSocket server and quitting the application gracefully.
    def handle_close_event(self, signal_received, frame) -> None:
        print("\nCtrl+C detected. Closing application...")
        self.stop_vision_worker()
        self.mjpeg_server.stop()
        self.websocket.stop_server()
        app.quit()


    """ Vehicle Control Functions """

    ## Function to perform an emergency stop
    # @description: This function is called periodically by a timer to check if an emergency stop condition is met (e.g., if the calculated braking distance plus a safety margin is greater than the distance to an obstacle). If the condition is met, it stops the vehicle and activates the emergency stop state.
    def emergency_stop(self) -> None:
        return
        print("Emergency stop check...")
        print(self.controller.distanz())
        return
        speed = self.controller.get_current_speed()
        break_distance = (speed/10) * (speed/10) * 0.5
        # if car is sliding but wheels are not turning it thinks the car stopped
        # maybe add a timer for minimum time to block user inputs
        if self.emergency_stop_active and speed > 0: 
            return
        else:
            self.emergency_stop_active = False
        # if break distance is greater than distance to obstacle + 20 cm, stop the car
        if break_distance >= self.controller.get_distance_to_obstacle() + 20:
            self.controller.stop()
            self.emergency_stop_active = True


if __name__ == "__main__":
    app = QCoreApplication([])
    main_app = MainApp()


    signal.signal(signal.SIGINT, main_app.handle_close_event)

    app.exec()