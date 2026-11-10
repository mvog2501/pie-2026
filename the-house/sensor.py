"""Card-arrival sensors. Each one has:
    wait_for_card(timeout, status) -> True when a card is in place, False when no more cards are coming
    wait_for_clear()               -> returns once the card has moved on
"""
import cv2


class BeamSensor:
    """IR break-beam on a GPIO pin."""

    def __init__(self, cfg, camera):
        from gpiozero import Button  # only installed on the Pi

        self.beam = Button(cfg["beam_pin"])

    def wait_for_card(self, timeout, status=None):
        # Typical IR receivers pull the pin LOW while the beam is intact, so "broken" = button released.
        # If your sensor is the opposite, swap wait_for_release and wait_for_press.
        return self.beam.wait_for_release(timeout=timeout)

    def wait_for_clear(self):
        self.beam.wait_for_press()


class KeyboardSensor:
    """Laptop stand-in for the beam: shows the camera feed; space = a card is in place, q = no more cards."""

    def __init__(self, cfg, camera):
        self.camera = camera
        self.roi = cfg.get("roi", [0, 0, 0, 0])

    def wait_for_card(self, timeout=None, status=None):
        """status: optional function frame -> text, drawn at the top of the window."""
        while True:
            frame = self.camera.capture()
            text = status(frame) if status else ""
            x, y, w, h = self.roi
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.imshow("card", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                return True
            if key == ord("q"):
                return False

    def wait_for_clear(self):
        pass


def open_sensor(cfg, camera):
    return {"beam": BeamSensor, "keyboard": KeyboardSensor}[cfg["sensor"]](cfg, camera)
