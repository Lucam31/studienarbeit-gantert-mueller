import drivers
from time import sleep

class Controller:
    def __init__(self, drivers):
        self.drivers = drivers
        self.in1 = 15
        self.in2 = 13
        self.pwm = 32
        self.stby = 11

    # Controller sind higher level und koordinieren die Driver (Logik, (komplexere) Abläufe)
    def test(self):
        self.drivers.initialize()
        self.drivers.setup_output(self.in1, initial=False)
        self.drivers.setup_output(self.in2, initial=False)
        self.drivers.setup_output(self.pwm, initial=True)
        self.drivers.setup_output(self.stby, initial=True)

        print("Pin {} initial value:".format(self.in1), self.drivers.read(self.in1))
        print("Pin {} value:".format(self.in2), self.drivers.read(self.in2))

        self.drivers.setup_pwm(self.pwm, frequency=1000, duty_cycle=50)
        print("Pin {} PWM setup with frequency 1000 Hz and duty cycle 50%".format(self.pwm))

        self.drivers.toggle(self.in2)
        print("Pin {} after toggle:".format(self.in2), self.drivers.read(self.in2))

        sleep(2)

        self.drivers.toggle(self.in2)
        print("Pin {} after toggle:".format(self.in2), self.drivers.read(self.in2))