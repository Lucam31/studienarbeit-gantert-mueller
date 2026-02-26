
import sys
from time import sleep
from PySide6.QtCore import QObject, QCoreApplication, QTimer, Signal, Slot, QUrl, QThread
from threading import Thread
from PySide6.QtWebSockets import QWebSocket 
from PySide6.QtNetwork import QHostAddress, QAbstractSocket

"""
TODO:
    - Implement reconnection logic
    - add variables from client??
    - remove variables from client??
"""

class Worker(QObject):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @Slot()
    def run(self):
        """Worker thread's run method"""
        self.client.run()
        # self.completed.emit()

class WebSocket(QObject):
    # SignalClientReceived = Signal(str)
    SignalSendMessage = Signal(str)
    def __init__(self, url="ws://127.0.0.1:50000", parent=None):
        super().__init__(parent)
        self.isConnected = False
        self.url = url
        self.retryCount = 0
        self.setup()

    def setup(self):
        print(f"Connecting to WebSocket server at {self.url}...")
        self.websocket = QWebSocket()
        self.websocket.connected.connect(self.on_connected)
        self.websocket.disconnected.connect(self.on_disconnected)
        self.websocket.textMessageReceived.connect(self.on_message)
        self.websocket.errorOccurred.connect(self.on_error)
        self.websocket.open(QUrl(self.url))
        self.val = False
        self.vars = None
        self.SignalSendMessage.connect(self.__send_message)
        self.closeEventOccured = False

        self.worker_thread = Thread(target=self.run)
        self.worker_thread.daemon = True
        print("WebSocket client setup complete.")

    @Slot()
    def on_connected(self):
        """Handle successful connection to the server"""
        print("Connected to server.")
        self.isConnected = True
        self.worker_thread.start()

    @Slot()
    def on_disconnected(self):
        if self.closeEventOccured:
            return
        """Handle disconnection from the server"""
        print("Disconnected from server.")
        self.isConnected = False
        self.closeEventOccured = True
        self.tryReconnect()

    @Slot(str)
    def on_message(self, message):
        """Handle incoming messages from the server"""
        message = eval(message)[0]
        # print(message)
        # print(f"Received from server: {message}")
        self.handle_message(message)

    @Slot()
    def on_error(self):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {self.websocket.errorString()}")

    @Slot()
    def __send_message(self, message: str):
        """Send a message to the server"""
        self.websocket.sendTextMessage(message)

    def tryReconnect(self):
        """Attempt to reconnect to the server if disconnected"""
        if self.isConnected:
            print("Already connected, no need to reconnect.")
            return
        # Reconnect not working yet
        self.websocket.close()
        while self.retryCount < 5:
            print(f"Attempting to reconnect... ({self.retryCount + 1}/5)")
            # Create a new QWebSocket instance and reconnect signals
            # self.websocket = QWebSocket()
            # self.websocket.connected.connect(self.on_connected)
            # self.websocket.disconnected.connect(self.on_disconnected)
            # self.websocket.textMessageReceived.connect(self.on_message)
            # self.websocket.errorOccurred.connect(self.on_error)
            # self.websocket.open(QUrl(self.url))
            self.setup()
            self.retryCount += 1
            sleep(3)
            if self.websocket.state() == QAbstractSocket.SocketState.ConnectedState:
                print("Reconnected successfully.")
                self.retryCount = 0
                return
        print("Max retry attempts reached. Could not reconnect.")
        sys.exit(1)

    def closeEvent(self):
        """Handle the close event"""
        self.closeEventOccured = True
        # sending a disconnect message is not optimal if multiple clients are connected to the websocket
        # self.websocket.sendTextMessage("disconnect")
        print("Closing WebSocket connection...")
        self.websocket.close()
        self.worker_thread.join()
        print("WebSocket connection closed.")
        sys.exit()

####################################
#   Write your custom code here    #
####################################

    def handle_message(self, message: str | list):
        """
        Process the incoming messages from the RTSI
        It is called upon receiving a message from the server
        Use this function to handle the message content
        """
        if isinstance(message, list):
            # message with watched variables, is sent by the server on every new connection with a client
            print(message)
            self.vars = message
            return
        splitMsg = message.split(';')
        print(f"Timestamp: {splitMsg[0]}")
        for var in splitMsg[1:]:
            print(f"{var.split(',')[0]}: {var.split(',')[-1]}")
        print("\n")

        # send messages to the RTSI with this command
        # self.SignalSendMessage.emit("set value <var1>:<val1>")

        # you can also set multiple vars at once
        # self.SignalSendMessage.emit("set value <var1>:<val1>;<var2>:<val2>;...")

        # here is an example with an actual var
        # self.SignalSendMessage.emit("set value sTest.bAllowCnt[0]:0;sTest.ulCnt[0]:0")

        # adding and removing variables to the RTSI isn't implemented yet
        # when it is implemented it will only be possible to add variables while the RTSI is disconnected
        # to add/remove variables from the RTSI disconnect and add/remove them using the vars identifier
        # self.SignalSendMessage.emit("add vars <var1>;<var2>;...") # also possible with only one var (add vars <var1>)

    def run(self):
        """
        This is the main loop of the RTSIClient Logic
        It will run in an endless loop and in it's own thread
        It will stop when closeEvent() is triggered by pressing ctrl + c in the console
        """
        # This Signal triggers the Connect Button in the RTSI Gui
        # Sending it while it is already connected won't have any effect
        # a disconnect message is also possible to stop the RTSI
        self.SignalSendMessage.emit("connect")
        while not self.closeEventOccured:
            # send messages via an emit of the signal so the send_message function gets executed in the main thread
            self.SignalSendMessage.emit("set value sTest.bAllowCnt[0]:" + str(1 if self.val else 0))
            self.val = not self.val
            # this sleep value is just an example so the variable gets changed every 2 seconds
            # you can adjust it to your needs
            sleep(2)

####################################
#                                  #
####################################


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import signal
    app = QApplication(sys.argv)
    client = WebSocket()

    signal.signal(signal.SIGINT, lambda s, f: client.closeEvent())

    sys.exit(app.exec())
