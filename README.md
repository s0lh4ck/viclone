<p align="center"><img src="branding/logo.png" alt="ViClone" height="80"></p>

# ViClone

Internal tool for authorized vishing exercises: clones a voice from audio/video
reference material and uses it either to generate scripted lines (text-to-speech) or,
live, as the microphone input of a softphone such as MicroSIP.

> Use only under a signed, authorized engagement with documented, informed consent
> from the person whose voice is processed. Voice is biometric/personal data — protect
> case material accordingly and delete it once the case is closed.

## Features

- Case-based workflow — client, target person, and authorization reference are
  required before anything else can run.
- Reference audio/video upload, auto-cleaned with `ffmpeg` + `pydub`.
- Text-to-speech cloning via Coqui XTTS-v2 (zero-shot, multilingual).
- Live voice-conversion pipeline for real calls, routed to a virtual audio cable that
  feeds a softphone's microphone input. Ships as a working passthrough stub — plug in a
  real engine (see `rvc_bridge/`) before using it in an actual exercise.
- Single-password login gate, audit logging, and a "close case" action that permanently
  deletes stored voice material.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set VICLONE_SECRET_KEY and VICLONE_PASSWORD
python app.py                # dev only — use `waitress-serve wsgi:application` in production
```

Requires `ffmpeg` and PortAudio (`portaudio19-dev` / `brew install portaudio`) on the
system. Open `http://127.0.0.1:5000`.

## Notes

- XTTS-v2 ships under Coqui's non-commercial license (CPML) — review it before
  commercial use.
- `rvc_bridge/train.py` and `rvc_bridge/realtime.py` document the exact contract ViClone
  expects from a real voice-conversion engine.
- `pytest` runs the unit test suite (schema/migration, filename validation, auth).
