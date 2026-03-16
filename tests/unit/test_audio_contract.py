import pytest

from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
)


def test_normalize_audio_fields_renders_lyrics_blocks():
    raw = {
        "genre_description": "J-pop idol track with bright synth layers and punchy drums.",
        "bpm": 128,
        "keyscale": "A minor",
        "seed": 42,
        "duration": 160,
        "lyrics_blocks": [
            {"section": "intro", "label": "Intro", "style": "Synth Rise", "lines": ["yeah", "turn it up"]},
            {"section": "chorus", "label": "Chorus", "style": "Pop Explosion", "lines": ["boom boom", "we ignite"]},
        ],
    }
    out = normalize_audio_fields(raw)
    assert out["bpm"] == 128
    assert out["keyscale"] == "A minor"
    assert "[Intro]" in out["lyrics"]
    assert "[Chorus]" in out["lyrics"]


def test_normalize_audio_fields_normalizes_keyscale_case():
    raw = {
        "genre_description": "Bright city-pop with glossy synths.",
        "bpm": 122,
        "keyscale": "C Major",
        "seed": 7,
        "duration": 120,
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "Pulse", "lines": ["light it up"]},
        ],
    }
    out = normalize_audio_fields(raw)
    assert out["keyscale"] == "C major"


def test_validate_audio_lyrics_language_accepts_japanese_dominant_lyrics():
    lyrics = "[Verse 1]\n雨のネオンが揺れてる\nまだ君の声が残ってる"
    validate_audio_lyrics_language(lyrics, "ja")


def test_validate_audio_lyrics_language_rejects_english_only_lyrics_for_japanese():
    lyrics = "[Chorus]\nNeon rain on the boulevard\nStay with me under city lights"
    with pytest.raises(RuntimeError, match="expected ja-dominant lyrics"):
        validate_audio_lyrics_language(lyrics, "ja")


def test_validate_audio_genre_description_language_accepts_english_brief():
    text = "Japanese city-pop with glossy electric piano, fretless bass, and warm analog pads. A mature female lead glides over a restrained disco pulse while the hook opens with soft guitar shimmer."
    validate_audio_genre_description_language(text)


def test_validate_audio_genre_description_language_rejects_japanese_brief():
    text = "上品なジャパニーズ・シティポップで、艶のあるエレピとコーラスギターを前に、温かなアナログパッドが夜景の奥行きを作る。"
    with pytest.raises(RuntimeError, match="expected English production brief"):
        validate_audio_genre_description_language(text)
