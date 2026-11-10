"""Cameras. Each one has capture() -> BGR frame (numpy array, height x width x 3)."""
import cv2

FLIPS = {"horizontal": 1, "vertical": 0, "both": -1}  # config "flip" -> cv2.flip code; "both" = rotate 180


def flipped(frame, cfg):
    return cv2.flip(frame, FLIPS[cfg["flip"]]) if cfg.get("flip") else frame


class PiCamera:
    """Raspberry Pi camera with exposure, gain and white balance locked, so every frame looks the same."""

    def __init__(self, cfg):
        from picamera2 import Picamera2  # only installed on the Pi

        self.cfg = cfg
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_video_configuration(main={"size": tuple(cfg["resolution"]), "format": "RGB888"}))
        # Short exposure freezes a moving card.
        self.cam.set_controls({
            "AeEnable": False,
            "AwbEnable": False,
            "ExposureTime": cfg["exposure_us"],
            "AnalogueGain": cfg["gain"],
            "ColourGains": tuple(cfg["colour_gains"]),
        })
        self.cam.start()  # stream continuously so capture() returns the next frame without startup lag

    def capture(self):
        return flipped(self.cam.capture_array(), self.cfg)


class Webcam:
    """Laptop webcam, for testing without the Pi."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.cam = cv2.VideoCapture(cfg.get("webcam_index", 0))
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["resolution"][0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["resolution"][1])
        if not self.cam.isOpened():
            raise RuntimeError("Could not open the webcam")

    def capture(self):
        ok, frame = self.cam.read()
        if not ok:
            raise RuntimeError("Webcam stopped sending frames")
        return flipped(frame, self.cfg)


def open_camera(cfg):
    return {"pi": PiCamera, "webcam": Webcam}[cfg["camera"]](cfg)
