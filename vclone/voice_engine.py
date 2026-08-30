import threading

from . import config

_lock = threading.Lock()
_tts_instance = None


def _load_engine():
    """Carga perezosa del modelo XTTS-v2 (pesado: solo se hace una vez por proceso)."""
    global _tts_instance
    if _tts_instance is None:
        with _lock:
            if _tts_instance is None:
                import torch
                from TTS.api import TTS

                device = "cuda" if torch.cuda.is_available() else "cpu"
                _tts_instance = TTS(config.TTS_MODEL_NAME).to(device)
    return _tts_instance


def synthesize(text, reference_wavs, language, output_path):
    """Genera audio con la voz clonada a partir de una o varias muestras de referencia."""
    tts = _load_engine()
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_wavs,
        language=language,
        file_path=output_path,
    )
    return output_path
