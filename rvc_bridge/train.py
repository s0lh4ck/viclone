"""Adapter: trains a real-time voice-conversion model from a directory of
cleaned reference WAV files.

This is a thin wrapper you fill in against whatever RVC-style toolkit
checkout you install locally (e.g. the Retrieval-based Voice Conversion
WebUI project). Exact APIs differ between forks/versions, so this repo does
not vendor or assume a specific one -- ViClone only needs the contract
below to be satisfied.

Contract expected by the ViClone app (see vclone/rvc_engine.py):
    python rvc_bridge/train.py --dataset <dir_of_wavs> --exp-name <name> \
        --out-dir <dir> --epochs <n>
On success, <out-dir>/model.pth (and, if your engine uses one,
<out-dir>/model.index) must exist.
"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Directory of cleaned reference WAV files")
    parser.add_argument("--exp-name", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--epochs", type=int, default=200)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # TODO: wire this up to your installed RVC toolkit, e.g.:
    #   sys.path.insert(0, "/path/to/Retrieval-based-Voice-Conversion-WebUI")
    #   from infer.modules.train import preprocess, extract_feature, train  # names vary by fork
    #   preprocess(args.dataset, ...)
    #   extract_feature(...)
    #   train(exp_name=args.exp_name, epochs=args.epochs, ...)
    #   # then copy/symlink the resulting weights to:
    #   #   os.path.join(args.out_dir, "model.pth")
    #   #   os.path.join(args.out_dir, "model.index")
    print(
        "rvc_bridge/train.py is a stub -- it has not been connected to a "
        "real training engine yet. See README.md > 'Wiring up the live "
        "voice conversion engine'.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
