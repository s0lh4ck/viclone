import os
import subprocess
import uuid

from pydub import AudioSegment, effects, silence

from . import config


class AudioProcessingError(RuntimeError):
    pass


def _run_ffmpeg(args):
    result = subprocess.run(
        ["ffmpeg", "-y", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise AudioProcessingError(
            f"ffmpeg failed: {result.stderr.decode(errors='ignore')[-500:]}"
        )


def is_allowed_filename(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[-1].lower() in config.ALLOWED_REFERENCE_EXTENSIONS
    )


def convert_to_wav(input_path, output_path, sample_rate=config.SAMPLE_RATE):
    """Extract/convert any audio or video input into mono PCM16 WAV."""
    _run_ffmpeg([
        "-i", input_path,
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-acodec", "pcm_s16le",
        output_path,
    ])


def clean_reference_audio(wav_path):
    """Normalize volume and trim long silences from a reference sample."""
    audio = AudioSegment.from_wav(wav_path)
    audio = effects.normalize(audio)

    chunks = silence.split_on_silence(
        audio,
        min_silence_len=400,
        silence_thresh=audio.dBFS - 16,
        keep_silence=200,
    )
    if chunks:
        cleaned = chunks[0]
        for chunk in chunks[1:]:
            cleaned += chunk
        audio = cleaned

    audio.export(wav_path, format="wav")
    return wav_path


def process_reference_upload(raw_path, case_storage_dir, original_filename):
    """Convert and clean an uploaded file (audio or video), return the resulting WAV filename."""
    os.makedirs(case_storage_dir, exist_ok=True)
    wav_name = f"{uuid.uuid4().hex}.wav"
    wav_path = os.path.join(case_storage_dir, wav_name)

    convert_to_wav(raw_path, wav_path)
    clean_reference_audio(wav_path)

    return wav_name
