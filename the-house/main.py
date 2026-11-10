"""Ties the parts together: sensor.py (card arrives) -> camera.py (frame) -> recognition.py (which card).

Usage:
    python main.py preview    # save preview.png with the ROI box drawn
    python main.py roi        # drag a box around the corner index (needs a display); saved to the config
    python main.py calibrate  # feed the deck in recognition.CARDS order, --passes times (default 3)
    python main.py run        # feed a shuffled deck, print its order

config.json is the Pi (camera + IR beam). Add --config config_laptop.json to use the webcam,
with the space bar standing in for the beam (q = no more cards).
"""
import argparse
import json
import os
import time

import cv2
import numpy as np

import recognition as rec
from camera import open_camera
from sensor import open_sensor


def frames(cfg, camera, sensor, status=None):
    """Yield one frame per card, until the sensor reports no more cards."""
    while sensor.wait_for_card(cfg["timeout_s"], status):
        time.sleep(cfg["trigger_delay_s"])
        yield camera.capture()
        sensor.wait_for_clear()


def preview(cfg, camera, sensor):
    frame = next(frames(cfg, camera, sensor, lambda f: "Seat a card, press space"), None)
    if frame is None:
        return
    x, y, w, h = cfg["roi"]
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
    cv2.imwrite("preview.png", frame)
    print("Saved preview.png")


def select_roi(cfg, camera, sensor, config_path):
    frame = next(frames(cfg, camera, sensor, lambda f: "Seat a card, press space"), None)
    if frame is None:
        return
    roi = [int(v) for v in cv2.selectROI("card", frame)]
    if min(roi[2:]) <= 2 * rec.PAD:
        print(f"Box too small: it must be over {2 * rec.PAD} px in each direction")
        return
    cfg["roi"] = roi
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"Saved ROI {roi} to {config_path}")


def calibrate(cfg, camera, sensor, passes):
    os.makedirs(cfg["templates"], exist_ok=True)
    for p in range(passes):
        input(f"Pass {p + 1}/{passes}: load the deck in order {rec.CARDS[0]}, {rec.CARDS[1]}, ... {rec.CARDS[-1]} "
              "(A-K of spades, hearts, diamonds, clubs) and press Enter")
        n = 0
        card = rec.CARDS[0]
        shots = frames(cfg, camera, sensor, lambda f: f"Pass {p + 1}/{passes}: show {card}, press space (q = stop)")
        for card in rec.CARDS:
            frame = next(shots, None)
            if frame is None:  # stopped early: the cards not shown just have fewer (or no) templates
                break
            cv2.imwrite(f"{cfg['templates']}/{card}_{p}.png", rec.preprocess(frame, cfg["roi"]))
            n += 1
        print(f"Saved {n} templates")


def run(cfg, camera, sensor):
    templates = rec.load_templates(cfg["templates"])
    rows = []

    def live_guess(frame):  # only shown by sensors with a window (the keyboard sensor)
        s = rec.score_card(rec.preprocess(frame, cfg["roi"]), templates)
        second, best = np.sort(s)[-2:]
        return f"{rec.CARDS[s.argmax()]}  {best:.3f}  margin {best - second:.3f}  | recorded {len(rows)}"

    print("Feed the deck...")
    for frame in frames(cfg, camera, sensor, live_guess):
        rows.append(rec.score_card(rec.preprocess(frame, cfg["roi"]), templates))
    if not rows:
        print("No cards seen")
        return
    order, flags = rec.resolve_order(np.array(rows), cfg["min_margin"])
    for i, card in enumerate(order):
        print(f"{i + 1:2d}. {card}{'  <-- check' if i in flags else ''}")
    if len(order) != len(rec.CARDS):
        print(f"Note: saw {len(order)} cards, a full deck is {len(rec.CARDS)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preview", "roi", "calibrate", "run"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--passes", type=int, default=3)
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    camera = open_camera(cfg)
    sensor = open_sensor(cfg, camera)

    if args.mode == "preview":
        preview(cfg, camera, sensor)
    elif args.mode == "roi":
        select_roi(cfg, camera, sensor, args.config)
    elif args.mode == "calibrate":
        calibrate(cfg, camera, sensor, args.passes)
    else:
        run(cfg, camera, sensor)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
