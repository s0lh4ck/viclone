"""Adapter: real-time voice conversion for live calls.

Reads audio from an input device (the auditor's microphone), converts it to
the trained target voice, and writes the result to an output device --
typically a virtual audio cable whose "output" side is selected as the
microphone in a softphone such as MicroSIP.

As shipped, this is a PASSTHROUGH stub: it copies input straight to output
so you can validate the audio device routing (mic -> ViClone -> virtual
cable -> MicroSIP) end to end before any voice conversion is involved.
Reimplementing a low-latency, artifact-free real-time voice conversion
engine from scratch is a large project in itself; plug in an existing,
tuned engine (e.g. the realtime module of the RVC-WebUI project, or
w-okada/voice-changer) at the marked point instead of building a new one --
it will sound far better than a first attempt would.

Contract expected by the ViClone app (see vclone/rvc_engine.py):
    python rvc_bridge/realtime.py --model <model.pth> --index <model.index> \
        --input-device <id> --output-device <id> --pitch <semitones>
Runs until it receives SIGTERM/SIGINT.
"""
import argparse
import signal
import sys

import sounddevice as sd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--index", required=False, default="")
    parser.add_argument("--input-device", type=int, required=True)
    parser.add_argument("--output-device", type=int, required=True)
    parser.add_argument("--pitch", type=float, default=0.0, help="Pitch shift in semitones")
    parser.add_argument("--block-ms", type=int, default=250)
    parser.add_argument("--samplerate", type=int, default=16000)
    args = parser.parse_args()

    print(
        f"[rvc_bridge] model={args.model} index={args.index or '(none)'} "
        f"input_device={args.input_device} output_device={args.output_device} "
        f"pitch={args.pitch}",
        file=sys.stderr,
    )

    # TODO: load a real conversion engine here, e.g.:
    #   sys.path.insert(0, "/path/to/Retrieval-based-Voice-Conversion-WebUI")
    #   from tools.rvc_for_realtime import RVC
    #   engine = RVC(model_path=args.model, index_path=args.index, pitch=args.pitch)
    # Then replace the passthrough line in `callback` below with:
    #   outdata[:] = engine.infer(indata)
    print(
        "[rvc_bridge] WARNING: running in PASSTHROUGH mode -- no voice "
        "conversion is applied yet. Wire up a real engine before using "
        "this for an actual exercise.",
        file=sys.stderr,
    )

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def callback(indata, outdata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        outdata[:] = indata

    blocksize = int(args.samplerate * args.block_ms / 1000)

    with sd.Stream(
        device=(args.input_device, args.output_device),
        samplerate=args.samplerate,
        blocksize=blocksize,
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        print("[rvc_bridge] running -- send SIGTERM/SIGINT to stop", file=sys.stderr)
        while running:
            sd.sleep(100)


if __name__ == "__main__":
    main()
