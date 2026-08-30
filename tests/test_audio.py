from vclone import audio


def test_allowed_extensions_accepts_known_media_types():
    assert audio.is_allowed_filename("call.mp3")
    assert audio.is_allowed_filename("meeting.MP4")
    assert audio.is_allowed_filename("sample.wav")


def test_allowed_extensions_rejects_unknown_or_missing():
    assert not audio.is_allowed_filename("payload.exe")
    assert not audio.is_allowed_filename("no_extension")
