from datetime import datetime

from functools import partial
import threading
import hardware.drivers
import time

class Controller:
    def __init__(self, drivers):
        self.drivers = drivers
        self.leftcurrent_speed = 0.0
        self.rightcurrent_speed = 0.0
        self.last_set_speed = 0.0
        self.max_speed_change_per_s = 120.0
        self._left_command = 0.0
        self._right_command = 0.0
        self._left_target = 0.0
        self._right_target = 0.0
        self._last_drive_ts = None
        self._hall_sensor_timeout_s = 5.0
        self._hall_sensor_timer = None
        
        # pull up for right hall sensor, pull down
        self.leftHallSensorPin = 23
        self.rightHallSensorPin = 24

        self.right1 = 27
        self.right2 = 22
        self.rightpwm = 12
        self.rightstby = 17

        
        self.left1 = 26
        self.left2 = 19
        self.leftpwm = 16 # is pwm1 so should work
        self.leftstby = 13 # should work too

        # ultrasonic sensor pins
        self.trigger = 14
        self.echo = 15
        
        # self.hall_sensor = 16 # choose a GPIO pin
        self.setup_pins()

        self.last_hall_sensor_time = time.time()
        self.wheel_circumference = 0.3927 # in meters
        self._reset_hall_sensor_timer()

    def _reset_hall_sensor_timer(self) -> None:
        if self._hall_sensor_timer is not None:
            self._hall_sensor_timer.cancel()
        self._hall_sensor_timer = threading.Timer(
            self._hall_sensor_timeout_s,
            self._handle_hall_sensor_timeout,
        )
        self._hall_sensor_timer.daemon = True
        self._hall_sensor_timer.start()

    def _handle_hall_sensor_timeout(self) -> None:
        # No hall sensor signal for the timeout window: assume stop.
        print("Reset")
        self.leftcurrent_speed = 0.0
        self.rightcurrent_speed = 0.0

    def setup_pins(self):
        """ Setup hall sensor pin """
        self.drivers.setup_input(self.leftHallSensorPin, pull="up")
        self.drivers.setup_input(self.rightHallSensorPin, pull="up")

        """ Setup callback for hall sensor """
        self.drivers.add_event_detect(self.leftHallSensorPin, "falling", callback=partial(self.sensorCallback, "left"))
        self.drivers.add_event_detect(self.rightHallSensorPin, "falling", callback=partial(self.sensorCallback, "right"))

        self.drivers.initialize()

        """ Setup motor driver pins. in1 and in2 control the direction of the motor, pwm controls the speed, and stby is used to enable/disable the motor driver. """
        # right motor
        self.drivers.setup_output(self.right1, initial=False)
        self.drivers.setup_output(self.right2, initial=False)
        self.drivers.setup_output(self.rightpwm, initial=True)
        self.drivers.setup_output(self.rightstby, initial=True)

        # left motor
        self.drivers.setup_output(self.left1, initial=False)
        self.drivers.setup_output(self.left2, initial=False)
        self.drivers.setup_output(self.leftpwm, initial=True)
        self.drivers.setup_output(self.leftstby, initial=True)

        """ Setup ultrasonic sensor pins """
        self.drivers.setup_output(self.trigger, initial=False)
        self.drivers.setup_input(self.echo, pull="down")
        self._distance_sensor_ready = False
        self.setup_distance_sensor()

    def setup_distance_sensor(self):
        if self._distance_sensor_ready:
            return

        self.drivers.setup_output(self.trigger, initial=False)
        self.drivers.setup_input(self.echo, pull="down")
        # HC-SR04 needs a short settle time before first reliable pulse.
        time.sleep(0.06)
        self._distance_sensor_ready = True

    def distanz(self):
        max_distance_m = 4.0
        speed_of_sound_m_s = 343.0
        # Roundtrip-Zeit fuer die Maximaldistanz plus Reserve gegen Scheduling/Jitter.
        max_echo_time = (2.0 * max_distance_m) / speed_of_sound_m_s
        echo_start_timeout = max_echo_time + 0.02
        echo_pulse_timeout = max_echo_time + 0.02

        # Trigger-Impuls: kurz LOW, dann 10 us HIGH, danach wieder LOW.
        self.drivers.write(self.trigger, False)
        time.sleep(0.000002)
        self.drivers.write(self.trigger, True)
        time.sleep(0.00001)
        self.drivers.write(self.trigger, False)

        # Auf steigende Echo-Flanke warten (Beginn der Laufzeitmessung).
        wait_start = time.perf_counter()
        while not self.drivers.read(self.echo):
            if time.perf_counter() - wait_start > echo_start_timeout:
                print("Timeout: Kein Echo-Start erkannt")
                return 1000

        StartZeit = time.perf_counter()
        StopZeit = StartZeit

        # Auf fallende Echo-Flanke warten (Ende der Laufzeitmessung).
        while self.drivers.read(self.echo):
            StopZeit = time.perf_counter()
            if StopZeit - StartZeit > echo_pulse_timeout:
                print("Timeout: Echo-Puls zu lang")
                return 1000

        # Zeit Differenz zwischen Start und Ankunft.
        TimeElapsed = StopZeit - StartZeit
        # Mit Schallgeschwindigkeit (34300 cm/s) multiplizieren und durch 2 teilen.
        distanz = (TimeElapsed * 34300) / 2

        print("Gemessene Distanz = %.1f cm" % distanz)
        return distanz

    def sensorCallback(self, side ):
        # Called if sensor triggers rising edge
        timestamp = time.time()
        time_diff = timestamp - self.last_hall_sensor_time
        self.last_hall_sensor_time = timestamp
        if side == "left":
            self.leftcurrent_speed = self.calc_speed(time_diff)
        else:
            self.rightcurrent_speed = self.calc_speed(time_diff)
        self._reset_hall_sensor_timer()

    def calc_speed(self, time_diff):
        if time_diff >= 4:
            # if hall sensor has not been triggered for more than 4 seconds, assume the car only just started moving again
            speed = 0.0
            print(f"Hall sensor triggered. Time since last trigger: {time_diff:.2f} seconds. Assuming car was stopped.")
        elif time_diff > 0:
            speed = self.wheel_circumference / time_diff
            print(f"Hall sensor triggered. Time since last trigger: {time_diff:.2f} seconds. Estimated speed: {speed:.2f} m/s.")
        return speed

    def get_current_speed(self):
        # if hall sensor has not been triggered for more than 4 seconds, assume the car has stopped
        return max(self.leftcurrent_speed, self.rightcurrent_speed)
        #return self.current_speed if (time.time() - self.last_hall_sensor_time) < 4.0 else 0.0

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        if value < min_value:
            return min_value
        if value > max_value:
            return max_value
        return value

    @staticmethod
    def _ramp(current: float, target: float, max_delta: float) -> float:
        if max_delta <= 0.0:
            return current
        if target > current + max_delta:
            return current + max_delta
        if target < current - max_delta:
            return current - max_delta
        return target

    def _apply_output(self, left_speed: float, right_speed: float) -> None:
        left_speed = float(self._clamp(left_speed, -100.0, 100.0))
        right_speed = float(self._clamp(right_speed, -100.0, 100.0))

        left_forward = left_speed >= 0.0
        right_forward = right_speed >= 0.0

        left_duty = abs(left_speed)
        right_duty = abs(right_speed)

        # Right motor direction (A)
        self.drivers.write(self.right1, not right_forward)
        self.drivers.write(self.right2, right_forward)
        self.drivers.setup_pwm(self.rightpwm, frequency=5000, duty_cycle=right_duty)

        # Left motor direction (B)
        self.drivers.write(self.left1, left_forward)
        self.drivers.write(self.left2, not left_forward)
        self.drivers.setup_pwm(self.leftpwm, frequency=5000, duty_cycle=left_duty)

        # Track last commanded speed magnitude for other logic.
        self.last_set_speed = max(left_duty, right_duty)

    def _apply_ramp(self) -> None:
        now = time.perf_counter()
        if self._last_drive_ts is None:
            self._left_command = self._left_target
            self._right_command = self._right_target
        else:
            dt = max(0.0, now - self._last_drive_ts)
            max_delta = self.max_speed_change_per_s * dt
            self._left_command = self._ramp(self._left_command, self._left_target, max_delta)
            self._right_command = self._ramp(self._right_command, self._right_target, max_delta)
        self._last_drive_ts = now

        self._apply_output(self._left_command, self._right_command)

    def update(self) -> None:
        """Apply the ramp toward the last commanded target."""
        self._apply_ramp()

    def drive_tank(self, left_speed: float, right_speed: float) -> None:
        """Drive left/right motors directly.

        Args:
            left_speed: Signed speed in range [-100, 100]. Sign controls direction.
            right_speed: Signed speed in range [-100, 100]. Sign controls direction.
        """
        self._left_target = float(self._clamp(left_speed, -100.0, 100.0))
        self._right_target = float(self._clamp(right_speed, -100.0, 100.0))
        self._apply_ramp()

    def drive_joystick(self, x: float, y: float) -> None:
        """Convert joystick values into differential motor speeds.

        `x` steers (left/right), `y` throttles (forward/back).

        Both inputs are expected in [-100, 100].
        """
        x = float(self._clamp(x, -100.0, 100.0))
        y = float(self._clamp(y, -100.0, 100.0))

        # Simple arcade mixing:
        # - y=100,x=0 => both motors +100
        # - y=0,x=100 => spin in place (left +100, right -100)
        # - y=50,x=50 => left 100, right 0
        left = y + x
        right = y - x
        left = self._clamp(left, -100.0, 100.0)
        right = self._clamp(right, -100.0, 100.0)

        if left == 0.0 and right == 0.0:
            self.drive_tank(left_speed=0.0, right_speed=0.0)
            return

        self.drive_tank(left_speed=left, right_speed=right)
    
    """
    def drive(self, speed: float, steering: float = 0.0, forward: bool = True):
        # calculate speed of each wheel based on steering input (steering is between -1 and 1, where -1 is full left and 1 is full right)
        # when steering fully right/left, one wheel should be stopped and the other should be at full speed
        self.last_set_speed = speed
        right_wheel_speed = speed * (1 - steering)
        left_wheel_speed = speed * (1 + steering)

        if right_wheel_speed < 0:
            right_wheel_speed = 0
        if left_wheel_speed < 0:
            left_wheel_speed = 0

        # Set right wheel direction and speed
        self.drivers.write(self.right1, not forward)
        self.drivers.write(self.right2, forward)
        self.drivers.setup_pwm(self.rightpwm, frequency=1000, duty_cycle=right_wheel_speed)

        # Set left wheel direction and speed
        self.drivers.write(self.left1, forward)
        self.drivers.write(self.left2, not forward)
        self.drivers.setup_pwm(self.leftpwm, frequency=1000, duty_cycle=left_wheel_speed)
    """
        
    def stop(self):
        if self._hall_sensor_timer is not None:
            self._hall_sensor_timer.cancel()
        self.leftcurrent_speed = 0.0
        self.rightcurrent_speed = 0.0
        self.drivers.write(self.right1, False)
        self.drivers.write(self.right2, False)
        self.drivers.setup_pwm(self.rightpwm, frequency=1000, duty_cycle=0)
        self.drivers.write(self.left1, False)
        self.drivers.write(self.left2, False)
        self.drivers.setup_pwm(self.leftpwm, frequency=1000, duty_cycle=0)
        self._left_command = 0.0
        self._right_command = 0.0
        self._left_target = 0.0
        self._right_target = 0.0
        self._last_drive_ts = time.perf_counter()
