# AI Music Edition

A GitHub Actions-based music-generation experiment with two workflows:

- **CPU Melody Prototype**: lightweight melody analysis and MIDI preview.
- **Full Song Generator (CPU)**: calls the open-source ACE-Step 1.5 model to attempt a full vocal/instrumental song from a style prompt and lyrics, optionally conditioned on an original audio recording.

## Generate a full song

1. Open [Actions](../../actions/workflows/full-song-cpu.yml).
2. Select **Full Song Generator (CPU)** and click **Run workflow**.
3. Optionally provide an HTTPS URL to an audio file containing the melody. The source file must be accessible to the GitHub runner without a login.
4. Enter lyrics, style, duration (start with 15 or 30 seconds), and the turbo model.
5. When the job finishes, download the **ai-music-full-song** artifact. It should contain `generated_song.wav`, the submitted lyrics, request/result metadata, and logs.

If no audio URL is provided, the model runs in text-to-music mode. If an audio URL is supplied, the workflow uses ACE-Step's cover task with the uploaded source audio. This is audio-conditioned generation; it does **not** guarantee exact note-for-note preservation of a melody.

## Important limitations

- The full workflow runs on a CPU-only GitHub-hosted runner. The model weights and dependencies are large, and inference may be very slow or fail due to runner memory/disk limits. The first run downloads the model; a GitHub Actions cache is enabled but is subject to GitHub cache limits.
- Hebrew lyrics can be supplied, but pronunciation, vocal alignment, and Hebrew singing quality are not guaranteed. This needs listening tests.
- The workflow has been committed but should be considered **unverified until an Actions run completes**. If it fails, download the artifact/logs and share the error.
- Only use source audio and lyrics you have permission to process.
- ACE-Step 1.5 code and weights have their own licenses/terms. Review the upstream [ACE-Step 1.5 repository](https://github.com/ace-step/ACE-Step-1.5) and model license before redistribution or commercial use. This repository's MIT license does not override third-party licenses.

## Existing prototype

See `.github/workflows/cpu-melody-prototype.yml` for the lightweight melody-to-MIDI smoke test. The two workflows are separate so the small test does not have to download the large generation model.

## Local prototype

Python 3.11 is recommended.

```bash
python -m pip install -r requirements.txt
python src/prototype.py --output-dir output --lyrics "Your lyrics here"
```
