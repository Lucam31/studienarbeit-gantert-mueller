import time

import hardware.drivers
from time import sleep

class Controller:
    def __init__(self, drivers):
        self.drivers = drivers
        self.in1 = 27
        self.in2 = 22
        self.pwm = 12
        self.stby = 17
        self.trigger = 14
        self.echo = 15
        self._distance_sensor_ready = False

    def setup_distance_sensor(self):
        if self._distance_sensor_ready:
            return

        self.drivers.setup_output(self.trigger, initial=False)
        self.drivers.setup_input(self.echo, pull="down")
        # HC-SR04 needs a short settle time before first reliable pulse.
        sleep(0.06)
        self._distance_sensor_ready = True

    # Controller sind higher level und koordinieren die Driver (Logik, (komplexere) Abläufe)
    def test(self):
        self.setup_distance_sensor()
        distance = self.distanz()
        if distance is None:
            # Retry once after sensor rest time to avoid first-shot misses.
            sleep(0.06)
            distance = self.distanz()
        print(distance)
        
        
        
        # self.drivers.setup_output(self.in1, initial=False)
        # self.drivers.setup_output(self.in2, initial=False)
        # self.drivers.setup_output(self.pwm, initial=True)
        # self.drivers.setup_output(self.stby, initial=True)

        # print("Pin {} initial value:".format(self.in1), self.drivers.read(self.in1))
        # print("Pin {} initial value:".format(self.in2), self.drivers.read(self.in2))
        # print("Pin {} initial value:".format(self.stby), self.drivers.read(self.stby))

        # self.drivers.setup_pwm(self.pwm, frequency=500, duty_cycle=50)
        # print("Pin {} PWM setup with frequency 500 Hz and duty cycle 50%".format(self.pwm))

        # self.drivers.toggle(self.in2)
        # print("Pin {} after toggle:".format(self.in2), self.drivers.read(self.in2))

        # sleep(2)

        # self.drivers.toggle(self.in2)
        # print("Pin {} after toggle:".format(self.in2), self.drivers.read(self.in2))

    def distanz(self):
        max_distance_m = 4.0
        speed_of_sound_m_s = 343.0
        # Roundtrip-Zeit fuer die Maximaldistanz plus Reserve gegen Scheduling/Jitter.
        max_echo_time = (2.0 * max_distance_m) / speed_of_sound_m_s
        echo_start_timeout = max_echo_time + 0.02
        echo_pulse_timeout = max_echo_time + 0.02

        # Trigger-Impuls: kurz LOW, dann 10 us HIGH, danach wieder LOW.
        self.drivers.write(self.trigger, False)
        sleep(0.000002)
        self.drivers.write(self.trigger, True)
        sleep(0.00001)
        self.drivers.write(self.trigger, False)

        # Auf steigende Echo-Flanke warten (Beginn der Laufzeitmessung).
        wait_start = time.perf_counter()
        while not self.drivers.read(self.echo):
            if time.perf_counter() - wait_start > echo_start_timeout:
                print("Timeout: Kein Echo-Start erkannt")
                return None

        StartZeit = time.perf_counter()
        StopZeit = StartZeit

        # Auf fallende Echo-Flanke warten (Ende der Laufzeitmessung).
        while self.drivers.read(self.echo):
            StopZeit = time.perf_counter()
            if StopZeit - StartZeit > echo_pulse_timeout:
                print("Timeout: Echo-Puls zu lang")
                return None

        # Zeit Differenz zwischen Start und Ankunft.
        TimeElapsed = StopZeit - StartZeit
        # Mit Schallgeschwindigkeit (34300 cm/s) multiplizieren und durch 2 teilen.
        distanz = (TimeElapsed * 34300) / 2

        print("Gemessene Distanz = %.1f cm" % distanz)
        return distanz