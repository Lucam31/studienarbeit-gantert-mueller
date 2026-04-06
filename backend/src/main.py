import time

from PySide6.QtCore import QObject, Signal, QTimer, QCoreApplication
from websocket.server import WebSocket
from utils.logger import Logger
import signal

import hardware.controller as controller
import hardware.drivers as drivers

class MainApp(QObject):
    def __init__(self):
        super().__init__()
        self.drivers = drivers.Drivers()
        self.controller = controller.Controller(self.drivers)
        self.test_routine()
        # self.websocket = WebSocket()
        # self.websocket.SignalMessageReceived.connect(self.handle_websocket_message)

    def test_routine(self):
        # Use Drivers abstraction (gpiozero+lgpio) for Raspberry Pi 5 compatibility.
        button_pin = 17  # BCM by default; call initialize(mode=drivers.BOARD) to use physical pin numbers
        self.drivers.initialize()
        self.drivers.setup_input(button_pin, pull="down")
        print("Test routine started")
        last_button_state = False
        while True: # Run forever
            button_state = self.drivers.read(button_pin)
            if button_state and not last_button_state:
                print("Button was pushed!")
                self.controller.test()
            last_button_state = button_state
            time.sleep(0.01)  # Sleep to avoid busy waiting

    def handle_websocket_message(self, message):
        print(f"Message received from WebSocket: {message}")
        # Hier kannst du die Logik implementieren, um auf die empfangenen Nachrichten zu reagieren

    def handle_close_event(self, signal_received, frame):
        print("\nCtrl+C detected. Closing application...")
        # self.websocket.stop_server()
        app.quit()



if __name__ == "__main__":
    app = QCoreApplication([])
    main_app = MainApp()
    # main_app.websocket.start_server(50000)

    signal.signal(signal.SIGINT, main_app.handle_close_event)

    app.exec()