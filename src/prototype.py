#!/usr/bin/env python3
"""CPU-only melody analysis smoke test; not a full singing generator yet."""
from __future__ import annotations

import argparse
import json
import platform
try:
    import resource
except ImportError:  # Windows local runs
    resource = None
import sys
import time
from pathlib import Path

import librosa
import numpy as np
import pretty_midi
import soundfile as sf


def make_test_audio(path: Path, seconds: float = 8.0, sr: int = 22050) -> None:
    """Create a short synthetic monophonic melody when no input is supplied."""
    notes = [60, 62, 64, 67, 64, 62, 60, 55]
    beat = 0.5
    audio = np.zeros(int(seconds * sr), dtype=np.float32)
    for i, note in enumerate(notes):
        start = int(i * beat * sr)
        end = min(len(audio), start + int(beat * sr))
        if end <= start:
            continue
        t = np.arange(end - start, dtype=np.float32) / sr
        envelope = np.minimum(1.0, np.minimum(t * 30.0, (len(t) / sr - t) * 30.0))
        audio[start:end] += (0.25 * np.sin(2 * np.pi * librosa.midi_to_hz(note) * t) * envelope).astype(np.float32)
    sf.write(path, audio, sr)


def midi_from_audio(audio_path: Path, midi_path: Path, preview_path: Path) -> dict:
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    if y.size == 0:
        raise ValueError("The input audio is empty.")
    duration = float(len(y) / sr)

    # piptrack is intentionally a lightweight baseline, not robust polyphonic transcription.
    pitches, magnitudes = librosa.piptrack(
        y=y, sr=sr, n_fft=2048, hop_length=256, fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"), threshold=0.15
    )
    max_bins = magnitudes.argmax(axis=0)
    freqs = pitches[max_bins, np.arange(pitches.shape[1])]
    strengths = magnitudes[max_bins, np.arange(magnitudes.shape[1])]
    valid = (freqs > 0) & (strengths > max(1e-5, float(strengths.max()) * 0.08))
    midi_float = np.zeros_like(freqs)
    midi_float[valid] = librosa.hz_to_midi(freqs[valid])
    midi_notes = np.rint(midi_float).astype(int)

    hop_seconds = 256 / sr
    instrument = pretty_midi.Instrument(program=pretty_midi_instrument_program("Acoustic Grand Piano"))
    segments = []
    current_note = None
    start_frame = 0
    for i, note in enumerate(midi_notes):
        candidate = int(note) if valid[i] and 24 <= note <= 96 else None
        if candidate != current_note:
            if current_note is not None:
                start = start_frame * hop_seconds
                end = i * hop_seconds
                if end - start >= 0.08:
                    instrument.notes.append(pretty_midi.Note(velocity=85, pitch=current_note, start=start, end=end))
                    segments.append({"pitch": current_note, "start": round(start, 3), "end": round(end, 3)})
            current_note = candidate
            start_frame = i
    if current_note is not None:
        start = start_frame * hop_seconds
        end = len(midi_notes) * hop_seconds
        if end - start >= 0.08:
            instrument.notes.append(pretty_midi.Note(velocity=85, pitch=current_note, start=start, end=end))
            segments.append({"pitch": current_note, "start": round(start, 3), "end": round(end, 3)})

    midi = pretty_midi.PrettyMIDI(initial_tempo=120)
    midi.instruments.append(instrument)
    midi.write(str(midi_path))
    # PrettyMIDI's built-in synthesizer is a simple sine-wave preview, not a production renderer.
    preview = midi.synthesize(fs=22050)
    if len(preview) == 0:
        preview = np.zeros(int(max(1, duration) * 22050), dtype=np.float32)
    sf.write(preview_path, preview, 22050)
    return {
        "input_duration_seconds": round(duration, 3),
        "sample_rate_hz": sr,
        "estimated_note_events": len(segments),
        "notes_preview": segments[:80],
        "warning": "Baseline piptrack is most suitable for clean monophonic audio; polyphonic recordings may be inaccurate.",
    }


def pretty_midi_instrument_program(name: str) -> int:
    # Kept separate to make the General MIDI instrument choice explicit.
    return pretty_midi.instrument_name_to_program(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-audio", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--lyrics", default="")
    parser.add_argument("--style", default="melody-preserving pop arrangement")
    args = parser.parse_args()

    started = time.time()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    input_audio = args.input_audio or out / "synthetic_test_melody.wav"
    if args.input_audio is None:
        make_test_audio(input_audio)

    report = {
        "project": "AI Music Edition",
        "stage": "cpu-melody-pipeline-smoke-test",
        "status": "started",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "lyrics_provided": bool(args.lyrics.strip()),
        "lyrics_note": "Lyrics are stored for the next integration stage; this prototype does not synthesize vocals.",
        "requested_style": args.style,
    }
    (out / "lyrics.txt").write_text(args.lyrics, encoding="utf-8")
    try:
        report.update(midi_from_audio(input_audio, out / "estimated_melody.mid", out / "melody_preview.wav"))
        report["status"] = "success"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = f"{type(exc).__name__}: {exc}"
        (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        raise
    report["elapsed_seconds"] = round(time.time() - started, 3)
    try:
        if resource is None:
            report["peak_rss_mb"] = None
        else:
            report["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform != "darwin" else 1024 * 1024), 1)
    except Exception:
        report["peak_rss_mb"] = None
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "elapsed_seconds", "peak_rss_mb", "estimated_note_events") if k in report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
