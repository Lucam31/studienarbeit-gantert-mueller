import RPi.GPIO as GPIO

class Drivers:
    def __init__(self):
        self.drivers = {}

    # Driver sind sehr low level und machen nur direkte Ansteuerung der Hardware
    def initialize(self, mode: int = GPIO.BCM, disable_warnings: bool = True) -> None:
        GPIO.setwarnings(not disable_warnings)
        GPIO.setmode(mode)

    def setup_output(self, pin: int, initial: bool = False) -> None:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH if initial else GPIO.LOW)
        self.drivers[pin] = {"mode": "out", "value": initial}

    def setup_input(self, pin: int, pull: str | None = None) -> None:
        pull_map = {
            "up": GPIO.PUD_UP,
            "down": GPIO.PUD_DOWN,
            None: GPIO.PUD_OFF,
        }
        if pull not in pull_map:
            raise ValueError("pull must be one of: 'up', 'down', None")

        GPIO.setup(pin, GPIO.IN, pull_up_down=pull_map[pull])
        self.drivers[pin] = {"mode": "in", "pull": pull}

    def write(self, pin: int, value: bool) -> None:
        if pin not in self.drivers or self.drivers[pin]["mode"] != "out":
            raise RuntimeError(f"Pin {pin} is not configured as output")
        GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
        self.drivers[pin]["value"] = value

    def read(self, pin: int) -> bool:
        if pin not in self.drivers:
            raise RuntimeError(f"Pin {pin} is not configured")
        return GPIO.input(pin) == GPIO.HIGH

    def toggle(self, pin: int) -> bool:
        current = self.read(pin)
        new_value = not current
        self.write(pin, new_value)
        return new_value

    def setup_pwm(self, pin: int, frequency: float, duty_cycle: float = 0.0) -> None:
        if pin not in self.drivers:
            self.setup_output(pin, initial=False)
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(duty_cycle)
        self.drivers[pin]["pwm"] = pwm
        self.drivers[pin]["frequency"] = frequency
        self.drivers[pin]["duty_cycle"] = duty_cycle

    def set_pwm_duty_cycle(self, pin: int, duty_cycle: float) -> None:
        pwm = self._get_pwm(pin)
        pwm.ChangeDutyCycle(duty_cycle)
        self.drivers[pin]["duty_cycle"] = duty_cycle

    def set_pwm_frequency(self, pin: int, frequency: float) -> None:
        pwm = self._get_pwm(pin)
        pwm.ChangeFrequency(frequency)
        self.drivers[pin]["frequency"] = frequency

    def stop_pwm(self, pin: int) -> None:
        pwm = self._get_pwm(pin)
        pwm.stop()
        self.drivers[pin].pop("pwm", None)

    def cleanup_pin(self, pin: int) -> None:
        if pin in self.drivers and "pwm" in self.drivers[pin]:
            self.drivers[pin]["pwm"].stop()
        GPIO.cleanup(pin)
        self.drivers.pop(pin, None)

    def cleanup(self) -> None:
        for pin, cfg in list(self.drivers.items()):
            if "pwm" in cfg:
                cfg["pwm"].stop()
        GPIO.cleanup()
        self.drivers.clear()

    def _get_pwm(self, pin: int):
        if pin not in self.drivers or "pwm" not in self.drivers[pin]:
            raise RuntimeError(f"No PWM configured on pin {pin}")
        return self.drivers[pin]["pwm"]