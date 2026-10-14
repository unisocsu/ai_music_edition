# AI Music Edition

CPU-only prototype for melody-conditioned song generation experiments on GitHub Actions.

## Current stage

This first iteration is a reproducible **pipeline smoke test**, not yet a full singing-song generator. It accepts an audio melody and lyrics, analyzes the audio, exports an estimated MIDI melody plus a synthesized preview WAV, and records a JSON report. The initial pitch tracker is intended for clean, mostly monophonic melodies; mixed recordings may need source separation or a dedicated transcription model.

## Run with GitHub Actions

1. Open **Actions → CPU Melody Prototype → Run workflow**.
2. Provide an HTTPS URL to a WAV/MP3 file (or leave it blank to run the built-in synthetic test).
3. Enter lyrics and an optional style description.
4. Download the `ai-music-prototype` artifact from the completed run.

Only use audio and lyrics you have permission to process. The workflow does not train models or download large model weights. Audio URLs are user-provided workflow inputs; use trusted sources.

## Local run

Python 3.11 is recommended.

```bash
python -m pip install -r requirements.txt
python src/prototype.py --output-dir output --lyrics "Your lyrics here"
# Optional input recording:
python src/prototype.py --input-audio melody.wav --output-dir output --lyrics "Your lyrics here"
```

## Planned stages

1. Validate CPU/RAM and audio-analysis pipeline.
2. Improve melody transcription and timing, with MIDI export.
3. Add accompaniment generation while preserving the melody.
4. Evaluate a singing synthesis model with explicit Hebrew-language and CPU benchmarks.
5. Integrate components only after measuring runtime, RAM, output quality, and model licenses.

## Licensing

Repository code is MIT-licensed. Third-party model weights and datasets are not included; each dependency/model must be reviewed under its own license before redistribution or commercial use. No non-commercial model weights are bundled in this prototype.
