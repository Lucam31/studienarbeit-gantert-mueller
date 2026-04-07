from datetime import datetime

import hardware.drivers
from time import sleep, time

class Controller:
    def __init__(self, drivers):
        self.drivers = drivers
        self.current_speed = 0.0
        self.last_set_speed = 0.0
        self.ain1 = 27
        self.ain2 = 22
        self.apwm = 12
        self.astby = 17
        # change bin1 and bin2 to other pins for second motor, 29 and 31 should work
        self.bin1 = 29
        self.bin2 = 31
        self.bpwm = 33 # is pwm1 so should work
        self.bstby = 36 # should work too

        self.hall_sensor = 16 # choose a GPIO pin
        self.setup_pins()

        self.last_hall_sensor_time = time()
        self.wheel_circumference = 0.2 # in meters

    def setup_pins(self):
        self.drivers.initialize()

        """ Setup motor driver pins. in1 and in2 control the direction of the motor, pwm controls the speed, and stby is used to enable/disable the motor driver. """
        # right motor
        self.drivers.setup_output(self.ain1, initial=False)
        self.drivers.setup_output(self.ain2, initial=False)
        self.drivers.setup_output(self.apwm, initial=True)
        self.drivers.setup_output(self.astby, initial=True)

        # left motor
        self.drivers.setup_output(self.bin1, initial=False)
        self.drivers.setup_output(self.bin2, initial=False)
        self.drivers.setup_output(self.bpwm, initial=True)
        self.drivers.setup_output(self.bstby, initial=True)

        """ Setup hall sensor pin """
        self.drivers.setup_input(self.hall_sensor, pull=None)

        """ Setup callback for hall sensor """
        self.drivers.add_event_detect(self.hall_sensor, "falling", callback=self.sensorCallback)

        """ Setup ultrasonic sensor pins """
        # self.drivers.setup_output(self.ultrasonic_trigger, initial=False)
        # self.drivers.setup_input(self.ultrasonic_echo, pull="down")
        self.trigger = 14
        self.echo = 15
        self._distance_sensor_ready = False
        self.setup_distance_sensor()

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

        print("Pin {} initial value:".format(self.ain1), self.drivers.read(self.ain1))
        print("Pin {} value:".format(self.ain2), self.drivers.read(self.ain2))

        self.drivers.setup_pwm(self.apwm, frequency=1000, duty_cycle=50)
        print("Pin {} PWM setup with frequency 1000 Hz and duty cycle 50%".format(self.apwm))

        self.drivers.toggle(self.ain2)
        print("Pin {} after toggle:".format(self.ain2), self.drivers.read(self.ain2))

        self.drivers.toggle(self.ain2)
        print("Pin {} after toggle:".format(self.ain2), self.drivers.read(self.ain2))

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

    def sensorCallback(self):
        # Called if sensor triggers rising edge
        timestamp = time()
        time_diff = timestamp - self.last_hall_sensor_time
        self.last_hall_sensor_time = timestamp
        if time_diff >= 4:
            # if hall sensor has not been triggered for more than 4 seconds, assume the car only just started moving again
            speed = 0.0
            print(f"Hall sensor triggered. Time since last trigger: {time_diff:.2f} seconds. Assuming car was stopped.")
        elif time_diff > 0:
            speed = self.wheel_circumference / time_diff
            print(f"Hall sensor triggered. Time since last trigger: {time_diff:.2f} seconds. Estimated speed: {speed:.2f} m/s.")
        self.current_speed = speed

    def get_current_speed(self):
        # if hall sensor has not been triggered for more than 4 seconds, assume the car has stopped
        return self.current_speed if (time() - self.last_hall_sensor_time) < 4.0 else 0.0
    
    def drive(self, speed: float, steering: float = 0.0, forward: bool = True):
        # calculate speed of each wheel based on steering input (steering is between -1 and 1, where -1 is full left and 1 is full right)
        # when steering fully right/left, one wheel should be stopped and the other should be at full speed
        self.last_set_speed = speed
        right_wheel_speed = speed * (1 - steering)
        left_wheel_speed = speed * (1 + steering)

        # Set right wheel direction and speed
        self.drivers.write(self.ain1, not forward)
        self.drivers.write(self.ain2, forward)
        self.drivers.setup_pwm(self.apwm, frequency=1000, duty_cycle=right_wheel_speed)

        # Set left wheel direction and speed
        self.drivers.write(self.bin1, forward)
        self.drivers.write(self.bin2, not forward)
        self.drivers.setup_pwm(self.bpwm, frequency=1000, duty_cycle=left_wheel_speed)

    def stop(self):
        self.drivers.write(self.ain1, False)
        self.drivers.write(self.ain2, False)
        self.drivers.setup_pwm(self.apwm, frequency=1000, duty_cycle=0)
        self.drivers.write(self.bin1, False)
        self.drivers.write(self.bin2, False)
        self.drivers.setup_pwm(self.bpwm, frequency=1000, duty_cycle=0)

    def get_distance_to_obstacle(self) -> float:
        # implement logic to get distance to obstacle using ultrasonic sensor
        return 100.0

