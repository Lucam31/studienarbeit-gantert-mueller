import time

from PySide6.QtCore import QObject, Signal, QTimer, QCoreApplication, QThread
from websocket.server import WebSocket
from utils.logger import Logger
import signal, json

import hardware.controller as controller
import hardware.drivers as drivers

class MainApp(QObject):
    def __init__(self):
        super().__init__()
        self.drivers = drivers.Drivers()
        self.controller = controller.Controller(self.drivers)
        self.emergency_stop_active = False
        # self.test_routine()
        self.websocket = WebSocket()
        self.websocket.SignalMessageReceived.connect(self.handle_websocket_message)
        self.websocket.start_server(50000)
        timer = QTimer(self)
        timer.timeout.connect(self.emergency_stop)
        timer.start(500)  # Call emergency_stop every 500 ms

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

    ## Callback function to handle messages received from the WebSocket server
    # @param msg_id: The ID of the message received from the client
    # @param payload: The payload of the message received from the client
    # @description: This function is called when a message is received from the WebSocket server. It processes the message and implements the logic to handle different types of messages based on their IDs.
    def handle_websocket_message(self, msg_id: str, payload: str) -> None:
        print(f"Message received from WebSocket: {payload}")
        # implement logic for handling messages from the WebSocket
        """ differenciate between message ids? one id for drive command, one for follow the line command, etc. """
        msg_id = json.loads(msg_id)
        payload = json.loads(payload)
        print(f"Message ID: {msg_id}, Payload: {payload}")
        if msg_id == "drive_command":
            # speed is value between -100 and 100, where negative values indicate reverse and positive values indicate forward
            # steering is value between -1 and 1, where -1 is full left and 1 is full right
            speed = payload["speed"]
            steering = payload["steering"]
            if speed > 0:
                self.controller.drive(speed, steering, True)
            elif speed < 0:
                self.controller.drive(-speed, steering, False)
            else:
                self.controller.stop()
        elif msg_id == "follow_line_command":
            # implement logic for follow the line command
            print("Follow line command received. Implement logic to follow the line.")
        else:
            print(f"Unknown message id: {msg_id}")

    ## Callback function to handle close event (e.g., when Ctrl+C is pressed)
    # @param signal_received: The signal received (e.g., SIGINT)
    # @param frame: The current stack frame (not used in this function)
    # @description: This function is called when a close event is triggered (e.g., when Ctrl+C is pressed in the console). It performs cleanup operations, such as stopping the WebSocket server and quitting the application gracefully.
    def handle_close_event(self, signal_received, frame) -> None:
        print("\nCtrl+C detected. Closing application...")
        self.websocket.stop_server()
        app.quit()


    """ Vehicle Control Functions """

    ## Function to perform an emergency stop
    # @description: This function is called periodically by a timer to check if an emergency stop condition is met (e.g., if the calculated braking distance plus a safety margin is greater than the distance to an obstacle). If the condition is met, it stops the vehicle and activates the emergency stop state.
    def emergency_stop(self) -> None:
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
    # main_app.websocket.start_server(50000)

    signal.signal(signal.SIGINT, main_app.handle_close_event)

    app.exec()