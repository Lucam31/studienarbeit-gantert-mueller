import os, sys, time, json, socket
# ensure the project's src directory is on sys.path so 'utils' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import Logger
from PySide6.QtCore import QObject, QTimer, QCoreApplication, Signal
from PySide6.QtWebSockets import QWebSocketServer
from PySide6.QtNetwork import QHostAddress


class WebSocket(QObject):
    SignalMessageReceived = Signal(str, str)
    def __init__(self):
        QObject.__init__(self)
        self.logger = Logger("WebSocket")
        self.port = 50000
        self.history = list()
        self.server = QWebSocketServer('WebSocket', QWebSocketServer.NonSecureMode)
        self.websockets = dict()
        self.sendTimer = QTimer()
        self.sendTimer.timeout.connect(self.update)
        self.sendTimer.start(100)
        self.address = QHostAddress.Any#QHostAddress("192.168.3.200")

    ## Update function to send new messages to clients
    # @description: This function is called periodically by a timer. It checks if there are new messages in the history and sends them to the clients. Each client has an index in the history, which is updated after sending messages.
    def update(self) -> None:
        for key, value in list(self.websockets.items()):
            try:
                if value < len(self.history):
                    data = '['
                    for i in range(value, len(self.history)):
                        data += json.dumps(self.history[i]) + ','
                    value = len(self.history)
                    data = data[:-1]
                    data += ']'
                    #print(f"Sending data to client: {data}")
                    key.sendTextMessage(data)
                    self.websockets[key] = value
            except Exception as e:
                self.logger.exception(f"Exception sending to clients: {e}.")

    ## Handle messages received from clients
    # @param message: The message received from the client
    # @description: This function is called when a message is received from a client.
    # It processes the JSON message and emits a signal to notify the main application.
    def handleClientMessage(self, message: json) -> None:
        """
        Payload format:
        {
            "id": "unique_message_id", needed?
            "payload": {
                "speed": "value1",
                "break": "true/false", break var or just break when speed is 0?
                "steering": "value2",
                ...
            }
        }
        """
        try:
            # Parse the JSON message
            data = json.loads(message)
            self.logger.info(f"Received JSON message: {data}")

            # Extract ID and payload
            message_id = data.get("id", "unknown")
            payload = data.get("payload", {})

            self.logger.info(f"Message ID: {message_id}, Payload: {payload}")

            # Process the payload (custom logic can be added here)
            # Example: Log the payload keys
            for key, value in payload.items():
                self.logger.info(f"Payload Key: {key}, Value: {value}")

            # Emit the original message
            self.SignalMessageReceived.emit(json.dumps(message_id), json.dumps(payload))
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON message: {message}. Error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while processing message: {message}. Error: {e}")
        
    ## Handle new client connections
    def newConnection(self) -> None:
        connection = self.server.nextPendingConnection()
        self.websockets[connection] = 0
        connection.textMessageReceived.connect(self.handleClientMessage)
        self.logger.info('New connection has been made from: {:s}'.format(connection.peerAddress().toString()))

    ## Start the WebSocket server
    # @param port: The port number to listen on
    # @description: This function starts the WebSocket server and listens for incoming connections. It also handles the case where the specified port is already in use by trying subsequent ports until it finds an available one or reaches a maximum number of attempts.
    # Returns True if the server started successfully, False otherwise.
    def start_server(self, port: int = 50000) -> bool:
        self.port = port
        triedPorts = 0
        # while(False == self.server.listen(QHostAddress.Any, port=self.port)):
        # self.logger.info(f'Trying to start WebSocket server on address {self.address.toString()}...')
        while not self.server.listen(self.address, port=self.port):
            if triedPorts > 10:
                self.logger.error(f'Could not open websocket on port {self.port}. Giving up.')
                return False
            else:
                self.logger.error(f'Could not open websocket on port {self.port}. Trying next port...')
                self.port += 1
                triedPorts += 1
        self.server.newConnection.connect(self.newConnection)
        #print(f"WebSocket server started on port {self.port}\nServer is reachable at ws://127.0.0.1:{self.port}")
        # self.logger.info(f'WebSocket server started on port {self.port}. Server is reachable at ws://{self.address.toString()}:{self.port}')
        return True
    
    ## Stop the WebSocket server
    def stop_server(self) -> None:
        self.server.close()
        self.logger.info(f'WebSocket server stopped.')
        #print(f"WebSocket server stopped.")

if __name__ == "__main__":
    app = QCoreApplication([])
    ws = WebSocket()
    ws.start_server(50000)
    app.exec()
