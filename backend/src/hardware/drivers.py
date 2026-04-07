from __future__ import annotations

from typing import Any


# Lazily imported in `_ensure_backend()` so this module can be imported
# on non-Raspberry-Pi dev machines without optional dependencies installed.
Device: Any = None
DigitalInputDevice: Any = None
DigitalOutputDevice: Any = None
PWMOutputDevice: Any = None
LGPIOFactory: Any = None


BCM = 11


# Raspberry Pi 40-pin header mapping (physical pin -> BCM GPIO number).
# Only pins which are actual GPIOs are included; power/ground pins are omitted.
_BOARD_TO_BCM: dict[int, int] = {
    3: 2,
    5: 3,
    7: 4,
    8: 14,
    10: 15,
    11: 17,
    12: 18,
    13: 27,
    15: 22,
    16: 23,
    18: 24,
    19: 10,
    21: 9,
    22: 25,
    23: 11,
    24: 8,
    26: 7,
    27: 0,
    28: 1,
    29: 5,
    31: 6,
    32: 12,
    33: 13,
    35: 19,
    36: 16,
    37: 26,
    38: 20,
    40: 21,
}


class Drivers:
    def __init__(self):
        self.drivers = {}
        self._mode = BCM

    def _ensure_backend(self) -> None:
        global Device, DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice, LGPIOFactory

        if Device is None or LGPIOFactory is None:
            try:
                import importlib

                gpiozero = importlib.import_module("gpiozero")
                pins_lgpio = importlib.import_module("gpiozero.pins.lgpio")
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "gpiozero/lgpio backend is not available. On Raspberry Pi OS install: "
                    "`sudo apt install python3-gpiozero python3-lgpio` "
                    "(or install `gpiozero` and `lgpio` via pip)."
                ) from exc

            Device = gpiozero.Device
            DigitalInputDevice = gpiozero.DigitalInputDevice
            DigitalOutputDevice = gpiozero.DigitalOutputDevice
            PWMOutputDevice = gpiozero.PWMOutputDevice
            LGPIOFactory = pins_lgpio.LGPIOFactory

        # Force lgpio backend for Raspberry Pi 5 compatibility.
        # This is safe to call multiple times.
        if not isinstance(getattr(Device, "pin_factory", None), LGPIOFactory):
            Device.pin_factory = LGPIOFactory()

    # Driver sind sehr low level und machen nur direkte Ansteuerung der Hardware
    def initialize(self, disable_warnings: bool = True) -> None:
        self._ensure_backend()
        # gpiozero always operates on BCM numbering; BOARD is supported by mapping.
        self._mode = BCM

        # `disable_warnings` is kept for API compatibility; gpiozero does not use it.
        _ = disable_warnings

    def setup_output(self, pin: int, initial: bool = False) -> None:
        self._ensure_backend()
        self._close_device(pin)
        device = DigitalOutputDevice(pin, initial_value=bool(initial))
        self.drivers[pin] = {
            "mode": "out",
            "value": bool(initial),
            "device": device,
            "pin": pin,
        }

    def setup_input(self, pin: int, pull: str | None = None) -> None:
        self._ensure_backend()
        pull_map: dict[str | None, bool | None] = {
            "up": True,
            "down": False,
            None: None,
        }
    
        if pull not in pull_map:
            raise ValueError("pull must be one of: 'up', 'down', None")

        self._close_device(pin)
        # With pull-up/down configured, gpiozero requires active_state=None.
        # `device.value` then reflects electrical HIGH/LOW directly.
        device = DigitalInputDevice(pin, pull_up=pull_map[pull])
        self.drivers[pin] = {"mode": "in", "pull": pull, "device": device, "pin": pin}

    def write(self, pin: int, value: bool) -> None:
        if pin not in self.drivers or self.drivers[pin]["mode"] != "out":
            raise RuntimeError(f"Pin {pin} is not configured as output")

        cfg = self.drivers[pin]
        if "pwm" in cfg:
            pwm = cfg["pwm"]
            duty = 100.0 if value else 0.0
            pwm.value = duty / 100.0
            cfg["duty_cycle"] = duty
            cfg["value"] = bool(value)
        else:
            device = cfg["device"]
            device.value = bool(value)
            cfg["value"] = bool(value)

    def read(self, pin: int) -> bool:
        #print("Reading pin {}...".format(pin))
        if pin not in self.drivers:
            raise RuntimeError(f"Pin {pin} is not configured")

        cfg = self.drivers[pin]
        if "pwm" in cfg:
            pwm = cfg["pwm"]
            return pwm.value > 0.0

        device = cfg.get("device")
        #print("Device for pin {}: {}".format(pin, device))
        if device is None:
            raise RuntimeError(f"Pin {pin} has no device configured")
        return bool(device.value)

    def toggle(self, pin: int) -> bool:
        current = self.read(pin)
        new_value = not current
        self.write(pin, new_value)
        return new_value

    def setup_pwm(self, pin: int, frequency: float, duty_cycle: float = 0.0) -> None:
        self._ensure_backend()
        
        if pin not in self.drivers:
            self.setup_output(pin, initial=False)
        if self.drivers[pin]["mode"] != "out":
            raise RuntimeError(f"Pin {pin} is not configured as output")

        cfg = self.drivers[pin]
        if "pwm" in cfg:
            # Re-create to match RPi.GPIO semantics (fresh PWM instance).
            self.stop_pwm(pin)

        self._close_device(pin)

        duty = float(duty_cycle)
        if duty < 0.0:
            duty = 0.0
        if duty > 100.0:
            duty = 100.0

        pwm = PWMOutputDevice(pin, frequency=float(frequency), initial_value=duty / 100.0)
        cfg["device"] = pwm
        cfg["pwm"] = pwm
        cfg["frequency"] = float(frequency)
        cfg["duty_cycle"] = duty
        cfg["value"] = duty > 0.0
        cfg["pin"] = pin

    def set_pwm_duty_cycle(self, pin: int, duty_cycle: float) -> None:
        pwm = self._get_pwm(pin)
        duty = float(duty_cycle)
        if duty < 0.0:
            duty = 0.0
        if duty > 100.0:
            duty = 100.0
        pwm.value = duty / 100.0
        self.drivers[pin]["duty_cycle"] = duty
        self.drivers[pin]["value"] = duty > 0.0

    def set_pwm_frequency(self, pin: int, frequency: float) -> None:
        pwm = self._get_pwm(pin)
        pwm.frequency = float(frequency)
        self.drivers[pin]["frequency"] = float(frequency)

    def stop_pwm(self, pin: int) -> None:
        pwm = self._get_pwm(pin)
        cfg = self.drivers[pin]
        was_on = pwm.value > 0.0
        pwm.close()
        cfg.pop("pwm", None)

        # Re-create a plain output device so `write()` keeps working.
        pin = cfg.get("pin", pin)
        cfg["value"] = bool(was_on)
        cfg["device"] = DigitalOutputDevice(pin, initial_value=bool(was_on))


    def cleanup_pin(self, pin: int) -> None:
        if pin in self.drivers:
            self._close_device(pin)
            self.drivers.pop(pin, None)

    def cleanup(self) -> None:
        for pin in list(self.drivers.keys()):
            self.cleanup_pin(pin)
        self.drivers.clear()

    def _get_pwm(self, pin: int) -> Any:
        if pin not in self.drivers or "pwm" not in self.drivers[pin]:
            raise RuntimeError(f"No PWM configured on pin {pin}")
        return self.drivers[pin]["pwm"]

    def _close_device(self, pin: int) -> None:
        cfg = self.drivers.get(pin)
        if not cfg:
            return

        device = cfg.pop("device", None)
        if device is not None:
            try:
                device.close()
            except Exception:
                pass

        pwm = cfg.get("pwm")
        if pwm is not None:
            try:
                pwm.close()
            except Exception:
                pass
            cfg.pop("pwm", None)

    # keine ahnung ob der scheiß mit gpiozero geht
    def add_event_detect(self, pin: int, edge: str, callback: Any) -> None:
        if pin not in self.drivers or self.drivers[pin]["mode"] != "in":
            raise RuntimeError(f"Pin {pin} is not configured as input")

        device = self.drivers[pin]["device"]
        if edge == "rising":
            device.when_activated = callback
        elif edge == "falling":
            device.when_deactivated = callback
        elif edge == "both":
            device.when_activated = callback
            device.when_deactivated = callback
        else:
            raise ValueError("edge must be one of: 'rising', 'falling', 'both'")