#!/usr/bin/env python3
"""Synthesise a small, licence-free sound-effect kit for reel.py.

Every effect is generated from noise and sine waves, so there is nothing to
license or credit. Swap any file for a recording you prefer, keeping the name.

Usage: python3 make_sfx.py OUT_DIR
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(d * SR)) / SR


def env(d, attack, decay):
    x = t(d)
    return np.minimum(1, x / max(attack, 1e-4)) * np.exp(-np.maximum(0, x - attack) / decay)


def band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def sweep_noise(d, f0, f1, peak):
    """Noise through a moving band-pass, loudest at `peak` seconds."""
    n = rng.normal(0, 1, int(d * SR))
    out = np.zeros_like(n)
    hop = 512
    for i in range(0, len(n), hop):
        p = i / len(n)
        fc = f0 * (f1 / f0) ** p
        out[i:i + hop] = band(n[max(0, i - 2048):i + hop], fc * 0.6, min(fc * 1.6, SR / 2 - 100))[-len(n[i:i + hop]):]
    x = t(d)
    shape = np.where(x < peak, (x / peak) ** 2, np.exp(-(x - peak) / 0.12))
    return out * shape


def norm(x, p=0.9):
    return x / (np.abs(x).max() + 1e-9) * p


def kit():
    k = {}
    k["whoosh"] = sweep_noise(0.6, 400, 3000, 0.27)
    k["swipe"] = sweep_noise(0.3, 1500, 6000, 0.09)
    k["riser"] = sweep_noise(2.0, 200, 5000, 1.825) + 0.3 * np.sin(2 * np.pi * (200 + 300 * t(2.0)) * t(2.0)) * (t(2.0) / 2) ** 3
    x = t(0.6)
    k["impact"] = np.sin(2 * np.pi * (90 * np.exp(-x * 6) + 40) * x) * env(0.6, 0.005, 0.18) + 0.3 * band(rng.normal(0, 1, len(x)), 80, 1200) * env(0.6, 0.002, 0.05)
    x = t(0.4)
    k["thud"] = np.sin(2 * np.pi * (70 * np.exp(-x * 8) + 45) * x) * env(0.4, 0.004, 0.09)
    x = t(0.15)
    k["pop"] = np.sin(2 * np.pi * (900 * np.exp(-x * 40) + 300) * x) * env(0.15, 0.002, 0.03)
    x = t(0.05)
    k["click"] = band(rng.normal(0, 1, len(x)), 2000, 8000) * env(0.05, 0.0005, 0.006)
    k["tick"] = np.sin(2 * np.pi * 2400 * x) * env(0.05, 0.0005, 0.008)
    x = t(1.2)
    k["ding"] = sum(a * np.sin(2 * np.pi * f * x) for f, a in [(1320, 1), (2640, 0.4), (3960, 0.15)]) * env(1.2, 0.003, 0.35)
    x = t(0.25)
    k["msg"] = np.concatenate([np.sin(2 * np.pi * 880 * x[:len(x) // 2]), np.sin(2 * np.pi * 1320 * x[:len(x) // 2])]) * env(0.25, 0.003, 0.08)[: (len(x) // 2) * 2]
    return {n: norm(v, 0.9 if n not in ("click", "tick") else 0.7) for n, v in k.items()}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sounds"
    os.makedirs(out, exist_ok=True)
    for name, x in kit().items():
        sf.write(os.path.join(out, name + ".wav"), x.astype(np.float32), SR)
    print("sound effects ready in", out)
