import pytest

from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
    validate_audio_lyrics_quality,
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
    lyrics = "[Verse 1]\n改札の音が静かに消える\n濡れた縁石にネオンが割れる"
    validate_audio_lyrics_language(lyrics, "ja")


def test_validate_audio_lyrics_language_accepts_korean_dominant_lyrics():
    lyrics = "[Verse 1]\n개찰구 불빛이 젖은 바닥에 번진다\n주머니 속 표 끝이 손끝에서 미지근해진다"
    validate_audio_lyrics_language(lyrics, "ko")


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


def test_validate_audio_lyrics_quality_rejects_english_leak_in_japanese_lines():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["timetable の数字が滲む"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["夜が降りて 街が眠る"]},
        {"section": "chorus", "label": "Chorus 2", "style": "lift", "lines": ["窓の向こう 灯りが流れる"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["このまま 歩き続ける"]},
    ]
    with pytest.raises(RuntimeError, match="Japanese lyrics leaked English words"):
        validate_audio_lyrics_quality(blocks, "ja")


def test_validate_audio_lyrics_quality_rejects_duplicate_chorus_growth():
    blocks = [
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["夜が降りて 街が眠る", "窓の向こう 灯りが流れる", "誰かの声 遠く聞こえる", "このまま 歩き続ける"]},
        {"section": "chorus", "label": "Chorus 2", "style": "lift", "lines": ["夜が降りて 街が眠る", "窓の向こう 灯りが流れる", "誰かの声 遠く聞こえる", "このまま 歩き続ける"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["夜が降りて 街が眠る", "窓の向こう 灯りが流れる", "誰かの声 遠く聞こえる", "このまま 歩き続ける"]},
    ]
    with pytest.raises(RuntimeError, match="too many repeated lines|repeats Chorus too closely"):
        validate_audio_lyrics_quality(blocks, "ja")


def test_validate_audio_lyrics_quality_accepts_english_growth():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["Station glass catches the blue", "Wet pavement folds the neon back"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["The city keeps my pulse awake", "Streetlight silver on the lane", "I carry your name through the smoke", "We keep moving through the rain"]},
        {"section": "chorus", "label": "Chorus 2", "style": "lift", "lines": ["The city lifts my pulse again", "Taxi windows comb the rain", "I keep your echo in my coat", "We move brighter through the rain"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["The whole night opens in my chest", "Streetlight halos crown the lane", "I call your name into the blue", "We move homeward through the rain"]},
    ]
    validate_audio_lyrics_quality(blocks, "en")


def test_validate_audio_lyrics_quality_rejects_overdense_korean_line():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["젖은개찰구불빛아래서나는아무숨도고르지못한채너의이름을너무길게불러보네"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["밤을 건너 네게 가", "젖은 빛이 반짝여", "개찰구 너머로", "너의 쪽이 환해져"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["젖은 빛이 더 커져", "밤을 건너 네게 가", "개찰구를 지나", "우리 이름이 빛나"]},
    ]
    with pytest.raises(RuntimeError, match="line too dense for singing"):
        validate_audio_lyrics_quality(blocks, "ko")


def test_validate_audio_lyrics_quality_rejects_chorus_without_short_hook_line():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["개찰구 불빛이 손끝에 스치고", "젖은 바닥 위로 발자국이 번져", "유리문에 숨을 고르고", "밤의 끝을 천천히 따라가"]},
        {
            "section": "chorus",
            "label": "Chorus",
            "style": "hook",
            "lines": [
                "젖은 네온이 내 마음 가장 깊은 곳까지 길게 번져와",
                "차가운 플랫폼 끝에서 나는 다시 한번 숨을 길게 고르고",
                "이 도시의 문장들이 오늘 밤 내 어깨 위로 천천히 내려와",
                "너를 향한 모든 마음이 늦은 불빛 속에서 겨우 또렷해져",
            ],
        },
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["밤을 건너 네게 가", "젖은 빛이 반짝여", "개찰구가 열려", "우리 이름이 빛나"]},
    ]
    with pytest.raises(RuntimeError, match="lacks a short memorable hook line"):
        validate_audio_lyrics_quality(blocks, "ko")
