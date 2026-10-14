"""Voiceover + caption timings for the demo, generated locally with Kokoro.

  pip install kokoro-onnx soundfile
  python3 voiceover.py <kokoro-v1.0.onnx> <voices-v1.0.bin>

Writes public/voiceover.wav, src/captions.json (@remotion/captions shape, ms) and
src/timeline.json (per-scene frame budgets). Each phrase is synthesised separately, so
phrase boundaries in the captions are measured, not guessed; words inside a phrase are
spaced by character length.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, TOTAL_S = 30, 80.0
VOICE, SPEED = "am_michael", 1.05
PHRASE_GAP, SCENE_LEAD = 0.12, 0.3

scenes = json.load(open(os.path.join(HERE, "script.json")))
k = Kokoro(sys.argv[1], sys.argv[2])

clips = []  # per scene: list of (phrase, audio)
for s in scenes:
    phrases = [p.strip() for p in re.split(r"(?<=[.,:!?])\s+", s["vo"]) if p.strip()]
    out = []
    for p in phrases:
        audio, sr = k.create(p, voice=VOICE, speed=SPEED, lang="en-us")
        # trim leading/trailing silence so the gaps are ours
        nz = np.where(np.abs(audio) > 0.01)[0]
        audio = audio[max(0, nz[0] - 240): nz[-1] + 480] if len(nz) else audio
        out.append((p, audio, sr))
    clips.append(out)

SR = clips[0][0][2]
speech = [sum(len(a) / SR for _, a, _ in c) + PHRASE_GAP * (len(c) - 1) for c in clips]
pad = (TOTAL_S - sum(speech) - SCENE_LEAD * len(scenes)) / len(scenes)
assert pad > 0.3, f"script too long for {TOTAL_S}s: speech={sum(speech):.1f}s"

track = np.zeros(int(TOTAL_S * SR), dtype=np.float32)
captions, timeline, t = [], [], 0.0
for s, c, sp in zip(scenes, clips, speech):
    start = t
    cur = start + SCENE_LEAD
    for phrase, audio, _ in c:
        i = int(cur * SR)
        track[i:i + len(audio)] += audio[: len(track) - i]
        dur = len(audio) / SR
        words = phrase.split()
        weights = np.array([len(w) + 1 for w in words], float)
        edges = np.concatenate([[0], np.cumsum(weights) / weights.sum()]) * dur
        for w, a, b in zip(words, edges[:-1], edges[1:]):
            captions.append({"text": " " + w if captions else w, "startMs": round((cur + a) * 1000),
                             "endMs": round((cur + b) * 1000), "timestampMs": None, "confidence": None})
        cur += dur + PHRASE_GAP
    length = SCENE_LEAD + sp + pad
    timeline.append({"id": s["id"], "from": round(start * FPS), "frames": round(length * FPS)})
    t += length

# frame budgets must sum to exactly TOTAL
timeline[-1]["frames"] = int(TOTAL_S * FPS) - timeline[-1]["from"]
sf.write(os.path.join(HERE, "public/voiceover.wav"), track, SR)
json.dump(captions, open(os.path.join(HERE, "src/captions.json"), "w"), indent=0)
json.dump(timeline, open(os.path.join(HERE, "src/timeline.json"), "w"), indent=1)
for x in timeline:
    print(x)
print(f"speech {sum(speech):.1f}s, pad/scene {pad:.2f}s")
