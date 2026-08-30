# ViClone

Internal tool for security audit teams: turns voice samples (audio or video) of a
person **within the authorized scope of a vishing exercise** into a cloned voice, used
either to generate scripted lines (text-to-speech) or, live, as the microphone input of
a softphone such as MicroSIP for a real-time call.

> **Intended use:** contracted, authorized social-engineering audits only, with
> documented, informed consent from the person whose voice is processed. Voice is
> biometric/personal data (GDPR): treat everything under `storage/` as confidential
> client material and delete it once the case is closed.

## What it does

1. You create a **case** per audit (client, target person, authorization reference —
   required to create a case at all).
2. You upload one or more audio/video files of that person. The app:
   - Extracts the audio track (if it's video) with `ffmpeg`.
   - Normalizes volume and trims long silences with `pydub`.
3. **Scripted lines:** type text and a language; the app renders a `.wav` with
   [Coqui XTTS-v2](https://github.com/coqui-ai/TTS), a zero-shot multilingual voice
   cloning model (no long training run needed — a clean sample of a few
   seconds/minutes is enough to synthesize new speech in that voice).
4. **Live calls:** you train a real-time voice-conversion model from the same
   reference material, then run live conversion that takes your microphone input,
   converts it to the target voice, and sends it to an output device you route into
   MicroSIP (or any other softphone) as its microphone. See
   "Wiring up the live voice conversion engine" below — this part ships as a working
   passthrough stub that you connect to a real conversion engine.

There is no Claude API integration: Claude is a text model and does not generate or
convert audio.

## Requirements

- Python 3.10+
- `ffmpeg` installed on the system (`apt install ffmpeg`, `brew install ffmpeg`, ...)
- PortAudio for live audio I/O (`apt install portaudio19-dev`, `brew install portaudio`)
- Recommended: an NVIDIA GPU + CUDA, both for XTTS-v2 synthesis speed and for training a
  real-time voice model at usable quality/speed
- A virtual audio cable to feed converted audio into a softphone (e.g.
  [VB-CABLE](https://vb-audio.com/Cable/) on Windows, where MicroSIP runs)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The first time you generate scripted audio, `TTS` will download the XTTS-v2 weights
(several GB) and ask you to accept its license
([Coqui Public Model License](https://coqui.ai/cpml/), non-commercial unless you hold a
license from Coqui) — review it before using this tool in a service billed to clients.
If you need a permissively licensed model for commercial use, swap it in
`vclone/voice_engine.py` (e.g. OpenVoice V2, MIT licensed).

## Usage

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

1. Create a case with the client name, target person, and authorization/contract
   reference (required field).
2. Upload reference voice material (mp3, wav, mp4, mov, ...).
3. For scripted lines: type the script text and generate audio.
4. For live calls: train a voice model for the case, then start live conversion,
   pick your microphone as the input device and your virtual cable as the output
   device, and point MicroSIP's microphone setting at that same virtual cable.

## Wiring up the live voice conversion engine

Real-time, low-latency, natural-sounding voice conversion is a hard problem on its
own — the projects that actually do it well (the realtime module of the
[RVC-WebUI project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI),
or [w-okada/voice-changer](https://github.com/w-okada/voice-changer)) are large, tuned
codebases built specifically for this. Rather than reimplement that from scratch,
ViClone ships a thin, replaceable adapter layer:

- `rvc_bridge/train.py` — called by the "Train voice model" button with
  `--dataset <reference_dir> --exp-name <name> --out-dir <dir> --epochs <n>`. It must
  produce `<out-dir>/model.pth` (and `model.index` if your engine uses one).
- `rvc_bridge/realtime.py` — called by "Start live conversion" with
  `--model --index --input-device --output-device --pitch`. It runs until stopped.

Both ship as **stubs**: `train.py` fails loudly telling you it isn't wired up yet, and
`realtime.py` runs a working **passthrough** (mic straight to output, no conversion) so
you can validate the device routing into MicroSIP before any model exists. To make it
real:

1. Install a real-time-capable RVC toolkit checkout of your choice.
2. In `rvc_bridge/train.py`, replace the stub with calls into that toolkit's
   preprocessing/feature-extraction/training pipeline, ending with the two output files
   above.
3. In `rvc_bridge/realtime.py`, replace the passthrough line in the audio callback with
   a call into that toolkit's real-time inference function.

`vclone/rvc_engine.py` only manages the subprocess lifecycle (start/stop/status) and
audio device listing (`sounddevice`) — it does not care which toolkit you plug in, as
long as the contract above is met.

## Structure

```
app.py                    # Flask routes
vclone/config.py          # paths and parameters
vclone/db.py               # SQLite schema (cases, references, generated outputs)
vclone/audio.py            # audio extraction and silence cleanup
vclone/voice_engine.py     # Coqui XTTS-v2 wrapper (scripted lines)
vclone/rvc_engine.py       # orchestration for training / live conversion subprocesses
rvc_bridge/train.py        # adapter stub: training entry point
rvc_bridge/realtime.py     # adapter stub: real-time conversion entry point (passthrough)
templates/, static/        # web UI
storage/, data/            # per-case data (git-ignored)
```

## Security and good practice

- Never commit anything under `storage/` or `data/` (already in `.gitignore`): it
  contains real people's voices and personal data.
- Keep the actual authorization/consent evidence (signed contract, email, etc.)
  alongside each case, outside this repository.
- Live calls may be subject to call-recording consent laws that vary by
  jurisdiction (one-party vs. two-party consent) — check with the client/legal before
  recording or storing call audio.
- Delete voice material once a case is closed unless the contract requires retaining it.
