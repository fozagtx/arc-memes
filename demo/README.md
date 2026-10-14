# Demo video

`arc-memecoin-intel-demo.mp4`: a 1:20 narrated demo (1920×1080). It shows the problem (bundled Arc launches draining new buyers), the install (`npx skills add fozagtx/arc-memes`), and a scan before buying.

It's built in Remotion with [snapcn](https://github.com/snapcndev/snapcn) components (`screen-recording`, `punch-lines`, `terminal-simulator`, `agent-steps`, `word-captions`, `wordmark-cut`), following snapcn's design rules: near-black page, one violet accent, no gradients or glows. The only custom scene is `src/scenes/RugStory.tsx`, the chart, bundle map and dump, because snapcn ships no chart component.

The Argus screenshots in `public/` are real. `$MOONARC`, Sam, and every address and number in the rug and scan scenes are fictional, and the video labels them on screen.

## Rebuild

```bash
npm install
pip install kokoro-onnx soundfile
# Kokoro model files: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
python3 voiceover.py kokoro-v1.0.onnx voices-v1.0.bin   # public/voiceover.wav + src/captions.json + src/timeline.json
npm run studio                                          # preview
npm run render                                          # out/arc-memecoin-intel-demo.mp4
```

The narration lives in `script.json`. Edit it, re-run `voiceover.py`, and the scene timings and captions follow automatically.
