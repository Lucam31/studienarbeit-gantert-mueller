import RPi.GPIO as GPIO

class Drivers:
    def __init__(self):
        self.drivers = {}

    # Driver sind sehr low level und machen nur direkte Ansteuerung der Hardware