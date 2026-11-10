"""Card recognition by template matching. No hardware imports, so it can be tested on any machine."""
import os

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

RANKS = "A 2 3 4 5 6 7 8 9 10 J Q K".split()
CARDS = [r + s for s in "SHDC" for r in RANKS]  # also the deck order used for calibration
PAD = 8  # pixels trimmed off each template edge, so matching can absorb small position shifts


def preprocess(frame, roi):
    """Crop the corner index from a camera frame and return it as a lightly blurred grayscale image."""
    x, y, w, h = roi
    gray = cv2.cvtColor(frame[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (3, 3), 0)


def load_templates(folder="templates"):
    """Load templates saved as <card>_<pass>.png, e.g. 10H_0.png."""
    templates = {card: [] for card in CARDS}
    for name in os.listdir(folder):
        img = cv2.imread(os.path.join(folder, name), cv2.IMREAD_GRAYSCALE)
        templates[name.split("_")[0]].append(img[PAD:-PAD, PAD:-PAD])
    return templates


def score_card(crop, templates):
    """Return a 52-long array: the best match score of the crop against each card's templates."""
    return np.array([
        max((cv2.matchTemplate(crop, t, cv2.TM_CCOEFF_NORMED).max() for t in templates[card]), default=-1.0)
        for card in CARDS
    ])


def resolve_order(scores, min_margin=0.02):
    """Assign each scanned card a distinct identity, maximising the total score.

    scores: (n_cards_seen, 52) array from score_card.
    Returns (order, flags): card names in scan order, and the positions worth double-checking
    (the assignment overrode the top guess, or the top two guesses were too close).
    """
    rows, cols = linear_sum_assignment(-scores)
    order = [CARDS[c] for c in cols]
    flags = []
    for i, c in zip(rows, cols):
        second, best = np.sort(scores[i])[-2:]
        if scores[i].argmax() != c or best - second < min_margin:
            flags.append(int(i))
    return order, flags
