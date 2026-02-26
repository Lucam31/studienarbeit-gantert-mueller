import os, sys, time, json, socket
# ensure the project's src directory is on sys.path so 'utils' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import Logger
from PySide6.QtCore import QObject, QTimer, QCoreApplication, QByteArray, QIODevice, Signal
from PySide6.QtSerialPort import QSerialPort
from PySide6.QtWebSockets import QWebSocketServer
from PySide6.QtNetwork import QHostAddress


class WebSocket(QObject):
    SignalMessageReceived = Signal(str)
    def __init__(self):
        QObject.__init__(self)
        self.logger = Logger("WebSocket")
        self.port = 50000
        # self.ip = socket.gethostbyname(socket.gethostname())
        # self.ip = "192.168.3.222"
        self.history = list()
        self.server = QWebSocketServer('WebSocket', QWebSocketServer.NonSecureMode)
        self.websockets = dict()
        self.sendTimer = QTimer()
        self.sendTimer.timeout.connect(self.update)
        self.sendTimer.start(100)

    ## Update function to send new messages to clients
    # @description: This function is called periodically by a timer. It checks if there are new messages in the history and sends them to the clients. Each client has an index in the history, which is updated after sending messages.
    def update(self):
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
    # It stores the message in a buffer and emits a signal to notify the main application.
    def handleClientMessage(self, message):
        #print(f"Received message from client: {message}")
        self.logger.info(f"Received message from client: {message}")
        self.SignalMessageReceived.emit(message)
        
    ## Handle new client connections
    def newConnection(self):
        connection = self.server.nextPendingConnection()
        self.websockets[connection] = 0
        connection.textMessageReceived.connect(self.handleClientMessage)
        #print(f"New connection has been made from: {connection.peerAddress().toString()}")
        self.logger.info('New connection has been made from: {:s}'.format(connection.peerAddress().toString()))
        # self.history.append(self.vars)

    def start_server(self, port: int = 50000) -> bool:
        self.port = port
        triedPorts = 0
        # while(False == self.server.listen(QHostAddress.Any, port=self.port)):
        while not self.server.listen(QHostAddress.Any, port=self.port):
            if triedPorts > 10:
                self.logger.error(f'Could not open websocket on port {self.port}. Giving up.')
                return False
            else:
                self.logger.error(f'Could not open websocket on port {self.port}. Trying next port...')
                self.port += 1
                triedPorts += 1
        self.server.newConnection.connect(self.newConnection)
        #print(f"WebSocket server started on port {self.port}\nServer is reachable at ws://127.0.0.1:{self.port}")
        self.logger.info(f'WebSocket server started on port {self.port}. Server is reachable at ws://127.0.0.1:{self.port}')
        return True
    
    def stop_server(self):
        self.server.close()
        self.logger.info(f'WebSocket server stopped.')
        #print(f"WebSocket server stopped.")

if __name__ == "__main__":
    app = QCoreApplication([])
    ws = WebSocket()
    ws.start_server(50000)
    app.exec()
