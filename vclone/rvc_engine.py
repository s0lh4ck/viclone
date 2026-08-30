import os
import subprocess
import threading

from . import config

_lock = threading.Lock()
_training_processes = {}
_live_processes = {}


def _bridge_path(name):
    return os.path.join(config.RVC_BRIDGE_DIR, name)


def model_paths(model_dir):
    return (
        os.path.join(model_dir, "model.pth"),
        os.path.join(model_dir, "model.index"),
    )


def start_training(case_id, reference_dir, model_dir, epochs=None):
    with _lock:
        existing = _training_processes.get(case_id)
        if existing is not None and existing.poll() is None:
            raise RuntimeError("Training is already running for this case.")

    os.makedirs(model_dir, exist_ok=True)
    log_path = os.path.join(model_dir, "train.log")
    log_file = open(log_path, "w")

    proc = subprocess.Popen(
        [
            config.RVC_PYTHON_BIN,
            _bridge_path("train.py"),
            "--dataset", reference_dir,
            "--exp-name", f"case_{case_id}",
            "--out-dir", model_dir,
            "--epochs", str(epochs or config.RVC_TRAIN_EPOCHS),
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    with _lock:
        _training_processes[case_id] = proc
    return proc


def training_status(case_id, model_dir):
    model_path, _ = model_paths(model_dir)
    with _lock:
        proc = _training_processes.get(case_id)

    if proc is not None and proc.poll() is None:
        return "training"
    if os.path.exists(model_path):
        return "ready"
    if proc is not None and proc.poll() not in (None, 0):
        return "failed"
    return "not_trained"


def list_audio_devices():
    import sounddevice as sd

    devices = sd.query_devices()
    inputs, outputs = [], []
    for idx, dev in enumerate(devices):
        entry = {"id": idx, "name": dev["name"]}
        if dev["max_input_channels"] > 0:
            inputs.append(entry)
        if dev["max_output_channels"] > 0:
            outputs.append(entry)
    return inputs, outputs


def start_live_conversion(case_id, model_dir, input_device, output_device, pitch=0.0):
    stop_live_conversion(case_id)

    model_path, index_path = model_paths(model_dir)
    if not os.path.exists(model_path):
        raise RuntimeError("No trained voice model for this case yet.")

    args = [
        config.RVC_PYTHON_BIN,
        _bridge_path("realtime.py"),
        "--model", model_path,
        "--index", index_path if os.path.exists(index_path) else "",
        "--input-device", str(input_device),
        "--output-device", str(output_device),
        "--pitch", str(pitch),
        "--samplerate", str(config.LIVE_SAMPLE_RATE),
    ]
    proc = subprocess.Popen(args)
    with _lock:
        _live_processes[case_id] = proc
    return proc


def stop_live_conversion(case_id):
    with _lock:
        proc = _live_processes.pop(case_id, None)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def live_status(case_id):
    with _lock:
        proc = _live_processes.get(case_id)
    return proc is not None and proc.poll() is None
