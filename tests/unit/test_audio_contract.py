import pytest

from ai_mv.core.contracts.prompt_normalize import (
    normalize_audio_fields,
    validate_audio_genre_description_language,
    validate_audio_lyrics_language,
    validate_audio_lyrics_quality,
)


def test_normalize_audio_fields_renders_lyrics_blocks():
    raw = {
        "genre_description": "J-pop track with bright synth layers and punchy drums.",
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


def test_normalize_audio_fields_allows_instrumental_intro_and_outro_blocks():
    raw = {
        "genre_description": "Synth pop with bright synths and clean drums.",
        "bpm": 112,
        "keyscale": "A major",
        "seed": 42,
        "duration": 160,
        "lyrics_blocks": [
            {"section": "intro", "label": "Intro", "style": "Instrumental Lift", "lines": []},
            {"section": "verse_1", "label": "Verse 1", "style": "Pulse", "lines": ["개찰구 불빛 아래 숨을 고르고"]},
            {"section": "outro", "label": "Outro", "style": "Tail", "lines": []},
        ],
    }
    out = normalize_audio_fields(raw)
    assert "[Intro]" not in out["lyrics"]
    assert "[Verse 1]" in out["lyrics"]
    assert "[Outro]" not in out["lyrics"]


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
    lyrics = "[Verse 1]\n젖은 불빛이 바닥 위로 번진다\n주머니 속 메모 끝이 손끝에서 미지근해진다"
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
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["Window glass catches the blue", "Wet pavement folds the neon back"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["The city keeps my pulse awake", "Streetlight silver on the lane", "I carry your name through the smoke", "We keep moving through the rain"]},
        {"section": "chorus", "label": "Chorus 2", "style": "lift", "lines": ["The city lifts my pulse again", "Taxi windows comb the rain", "I keep your echo in my coat", "We move brighter through the rain"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["The whole night opens in my chest", "Streetlight halos crown the lane", "I call your name into the blue", "We move homeward through the rain"]},
    ]
    validate_audio_lyrics_quality(blocks, "en")


def test_validate_audio_lyrics_quality_accepts_hook_validation_compact_line_budgets():
    blocks = [
        {"section": "intro", "label": "Intro", "style": "setup", "lines": []},
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["Dashboard glow", "Rain on the glass"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["Stay neon", "Drive me home"]},
        {"section": "outro", "label": "Outro", "style": "tail", "lines": []},
    ]

    validate_audio_lyrics_quality(
        blocks,
        "en",
        line_budgets={"Intro": 0, "Verse 1": 2, "Chorus": 2, "Outro": 0},
        section_bars={"intro": 4, "verse_1": 4, "chorus": 4, "outro": 4, "final_chorus_bonus": 0},
    )


def test_validate_audio_lyrics_quality_rejects_overworded_two_line_hook_validation_chorus():
    blocks = [
        {"section": "intro", "label": "Intro", "style": "setup", "lines": []},
        {
            "section": "chorus",
            "label": "Chorus",
            "style": "hook",
            "lines": [
                "Neon stay with me",
                "Tail lights blur and the lonely night lets us breathe",
            ],
        },
        {"section": "outro", "label": "Outro", "style": "tail", "lines": []},
    ]

    with pytest.raises(RuntimeError, match="Chorus hook line has too many words"):
        validate_audio_lyrics_quality(
            blocks,
            "en",
            line_budgets={"Intro": 0, "Chorus": 2, "Outro": 0},
            section_bars={"intro": 4, "chorus": 12, "outro": 4, "final_chorus_bonus": 0},
        )


def test_validate_audio_lyrics_quality_rejects_overworded_three_line_hook_validation_chorus():
    blocks = [
        {
            "section": "chorus",
            "label": "Chorus",
            "style": "hook",
            "lines": [
                "Your signal drifts through the desert dawn",
                "Say my name when the static is gone",
                "Stay on the line",
            ],
        },
        {"section": "outro", "label": "Outro", "style": "tail", "lines": ["Let it close", "Let it close"]},
    ]

    with pytest.raises(RuntimeError, match="Chorus hook line has too many words"):
        validate_audio_lyrics_quality(
            blocks,
            "en",
            line_budgets={"Intro": 0, "Verse 1": 0, "Pre-Chorus": 0, "Chorus": 3, "Outro": 2},
            section_bars={"intro": 0, "verse_1": 0, "pre_chorus": 0, "chorus": 12, "outro": 4, "final_chorus_bonus": 0},
        )


def test_validate_audio_lyrics_quality_rejects_nonrepeated_hook_validation_outro_tag():
    blocks = [
        {
            "section": "chorus",
            "label": "Chorus",
            "style": "hook",
            "lines": ["Stay on the line", "Hear me now", "Stay on the line"],
        },
        {
            "section": "outro",
            "label": "Outro",
            "style": "tail",
            "lines": ["Warm in my hands, you fade to gold", "I let you go, and still you stay"],
        },
    ]

    with pytest.raises(RuntimeError, match="Outro tag should repeat exactly"):
        validate_audio_lyrics_quality(
            blocks,
            "en",
            line_budgets={"Intro": 0, "Verse 1": 0, "Pre-Chorus": 0, "Chorus": 3, "Outro": 2},
            section_bars={"intro": 0, "verse_1": 0, "pre_chorus": 0, "chorus": 12, "outro": 4, "final_chorus_bonus": 0},
        )


def test_validate_audio_lyrics_quality_rejects_overdense_korean_line():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["젖은불빛아래서나는아무숨도고르지못한채너의이름을너무길게불러보네"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["밤을 건너 네게 가", "젖은 빛이 반짝여", "불빛 너머로", "너의 쪽이 환해져"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["젖은 빛이 더 커져", "밤을 건너 네게 가", "빛을 지나", "우리 이름이 빛나"]},
    ]
    with pytest.raises(RuntimeError, match="line too dense for singing"):
        validate_audio_lyrics_quality(blocks, "ko")


def test_validate_audio_lyrics_quality_allows_short_english_hook_in_korean():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["젖은 불빛 아래 숨을 고르고", "젖은 바닥 위로 발끝이 먼저 가"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["Super shy, 네 이름이 번져", "젖은 거리 위로 마음이 가", "초록 불빛 따라 더 가까워져", "오늘 밤 끝에서 네게 닿아"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["Super shy, 밤이 더 열려", "젖은 불빛 끝에 두 손이 닿아", "도시의 끝에서 네온이 번져", "오늘 밤 끝내 너를 안아"]},
    ]
    validate_audio_lyrics_quality(blocks, "ko")


def test_validate_audio_lyrics_quality_rejects_long_english_sentence_in_korean():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["젖은 불빛 아래 숨을 고르고", "젖은 바닥 위로 발끝이 먼저 가"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["I will always run to you through the city tonight", "젖은 거리 위로 마음이 가", "초록 불빛 따라 더 가까워져", "오늘 밤 끝에서 네게 닿아"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["밤을 건너 네게 가", "젖은 빛이 반짝여", "불빛이 열려", "우리 이름이 빛나"]},
    ]
    with pytest.raises(RuntimeError, match="expected readable Korean lines|too much English"):
        validate_audio_lyrics_quality(blocks, "ko")


def test_validate_audio_lyrics_quality_rejects_chorus_without_short_hook_line():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["젖은 불빛이 손끝에 스치고", "젖은 바닥 위로 발자국이 번져", "유리문에 숨을 고르고", "밤의 끝을 천천히 따라가"]},
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
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["밤을 건너 네게 가", "젖은 빛이 반짝여", "불빛이 열려", "우리 이름이 빛나"]},
    ]
    with pytest.raises(RuntimeError, match="lacks a short memorable hook line"):
        validate_audio_lyrics_quality(blocks, "ko")


def test_validate_audio_lyrics_quality_rejects_overpacked_four_bar_bridge():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["終電あとの道で息を止める", "窓の灯りだけが少し揺れる"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["夜はまだ終わらない", "駅前の風がほどける", "君の影だけ遠くなる", "それでも歩いていく"]},
        {
            "section": "bridge",
            "label": "Bridge",
            "style": "turn",
            "lines": [
                "改札の向こうの気配をまだ数えている",
                "眠れない窓辺で朝の輪郭を抱えこむ",
                "曲がるたび言いそびれた言葉が増える",
                "今夜だけ長い説明を続けてしまう",
            ],
        },
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["夜はまだ終わらない", "鍵を開けて進んでいく", "君のいない部屋の奥で", "新しい朝を迎えにいく"]},
    ]
    with pytest.raises(RuntimeError, match="4-bar Bridge"):
        validate_audio_lyrics_quality(
            blocks,
            "ja",
            section_bars={"verse": 8, "chorus": 8, "bridge": 4, "final_chorus_bonus": 8},
        )


def test_validate_audio_lyrics_quality_rejects_long_eight_bar_chorus_phrasing():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["終電あとの坂で立ち止まる", "ポケットの鍵が少し冷たい"]},
        {
            "section": "chorus",
            "label": "Chorus",
            "style": "hook",
            "lines": [
                "まだ戻れない",
                "歩道橋の上で言えなかった気持ちだけがまだ残る",
                "見送った背中だけが夜の窓にゆっくり伸びていく",
                "笑っていた横顔ばかり今も長く揺れ続けている",
                "あの角を曲がれば何かが戻る気がまだしてしまう",
            ],
        },
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["まだ行ける", "夜を越える", "この街ごと抱いて", "朝へ向かう"]},
    ]
    with pytest.raises(RuntimeError, match="8-bar chorus|Chorus phrasing"):
        validate_audio_lyrics_quality(
            blocks,
            "ja",
            section_bars={"verse": 8, "chorus": 8, "final_chorus_bonus": 8},
        )


def test_validate_audio_lyrics_quality_accepts_bar_fit_for_short_form_japanese_city_pop():
    blocks = [
        {"section": "intro", "label": "Intro", "style": "lift", "lines": []},
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["終電あとの坂を歩く", "ネオンが靴先でほどける", "言えないままの息を持つ", "窓の灯りだけ見ていた"]},
        {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["もう少しだけ", "ここにいてよ", "朝の前まで"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["まだ行ける", "夜はほどける", "君のいない街でも", "光の方へ進む"]},
        {"section": "verse_2", "label": "Verse 2", "style": "shift", "lines": ["改札の音が背を押す", "ポケットで鍵が鳴っている", "昨日の影は薄くなる", "この街にも朝が来る"]},
        {"section": "bridge", "label": "Bridge", "style": "turn", "lines": ["戻れない夜もある", "それでも前を見る", "白い朝が差しこむ"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["まだ行ける", "夜を越えて", "君のいない部屋でも", "新しい光を点ける", "この街でまた始める"]},
        {"section": "outro", "label": "Outro", "style": "tail", "lines": []},
    ]
    validate_audio_lyrics_quality(
        blocks,
        "ja",
        line_budgets={
            "Intro": 0,
            "Verse 1": 5,
            "Pre-Chorus": 3,
            "Chorus": 5,
            "Verse 2": 5,
            "Bridge": 3,
            "Final Chorus": 5,
            "Outro": 0,
        },
        section_bars={
            "intro": 8,
            "verse": 8,
            "pre_chorus": 8,
            "chorus": 8,
            "bridge": 4,
            "outro": 8,
            "final_chorus_bonus": 8,
        },
    )


def test_validate_audio_lyrics_quality_rejects_sixteen_bar_final_chorus_that_underdelivers():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["終電あとの坂を歩く", "ネオンが靴先でほどける", "言えないままの息を持つ", "窓の灯りだけ見ていた"]},
        {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["もう少しだけ", "ここにいてよ", "朝の前まで"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["まだ行ける", "夜はほどける", "君のいない街でも", "光の方へ進む"]},
        {"section": "bridge", "label": "Bridge", "style": "turn", "lines": ["戻れない夜もある", "それでも前を見る", "白い朝が差しこむ"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["まだ行ける", "夜を越えて", "君のいない部屋でも", "新しい光を点ける"]},
    ]
    with pytest.raises(RuntimeError, match="Final Chorus underuses"):
        validate_audio_lyrics_quality(
            blocks,
            "ja",
            section_bars={
                "verse": 8,
                "pre_chorus": 8,
                "chorus": 8,
                "bridge": 4,
                "final_chorus_bonus": 8,
            },
        )


def test_validate_audio_lyrics_quality_rejects_pre_chorus_that_is_too_broad_for_chorus_contrast():
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["終電あとの坂を歩く", "ネオンが靴先でほどける", "言えないままの息を持つ", "窓の灯りだけ見ていた"]},
        {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["もう少しだけこの街の夜を全部抱えていたい", "まだ言えなかった気持ちだけが胸の奥で渦を巻く", "朝の前まであなたの影を長く追いかけてしまう", "それでも今は戻れないまま揺れ続けている"]},
        {"section": "chorus", "label": "Chorus", "style": "hook", "lines": ["まだ行ける", "夜はほどける", "君のいない街でも", "光の方へ進む"]},
        {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["まだ行ける", "夜を越えて", "君のいない部屋でも", "新しい光を点ける", "この街でまた始める"]},
    ]
    with pytest.raises(RuntimeError, match="Pre-Chorus should stay tighter|Pre-Chorus phrasing is too broad"):
        validate_audio_lyrics_quality(
            blocks,
            "ja",
            section_bars={
                "verse": 8,
                "pre_chorus": 8,
                "chorus": 8,
                "final_chorus_bonus": 8,
            },
        )
