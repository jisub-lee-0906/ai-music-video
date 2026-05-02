import pytest

import ai_mv.engines.acestep_1_5_aio.planner as audio_planner


def _prompt_plan(**extra):
    plan = {
        "tags": "Synth-Pop, solo female, airy and emotional",
        "language": "ko",
        "genre_head": "Synth-Pop",
        "vocal_profile": "solo female",
        "vocal_tone": "airy and emotional",
        "audio_direction": "late-night breakup song that grows from restraint to direct release",
        "hook_direction": "short wet-city hook with a clear final lift",
        "hook_english_fragments": ["all night", "call my name"],
        "negative_direction": "avoid spectacle clutter",
        "duration": 150,
        "bpm": 108,
        "seed": 31,
        "quality": "high",
        "filename_prefix": "run_audio",
        "line_budgets": {
            "Intro": 0,
            "Verse 1": 4,
            "Verse 2": 4,
            "Pre-Chorus": 3,
            "Pre-Chorus 2": 3,
            "Chorus": 4,
            "Chorus 2": 4,
            "Final Chorus": 5,
            "Bridge": 2,
            "Outro": 0,
        },
        "terminal_end_tag": True,
        "final_chorus_required": False,
        "outro_required": False,
    }
    plan.update(extra)
    return plan


def test_audio_prompt_is_compact_and_keeps_core_contract():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "strict JSON only" in prompt
    assert "genre_description,bpm,keyscale,seed,duration,lyrics_blocks" in prompt
    assert "section,label,style,role,change,line_count" in prompt
    assert "Planner seed=31." in prompt
    assert "not the workflow execution seed" in prompt
    assert "The final render format is [tags], then bracketed lyrics, then [Outro], then [end]" in prompt
    assert "genre_description is the future [tags] block" in prompt
    assert "core instruments, arrangement energy, and vocal character" in prompt
    assert "Choose a songform that fits a modern short-form song around two and a half to three minutes" in prompt
    assert "Respect these minimum line counts" in prompt
    assert "Pre-Chorus>= 3" in prompt
    assert "Prefer a strong beginning-middle-turn-resolution arc" in prompt
    assert "Keep Intro instrumental." in prompt
    assert "director_brief_intent" not in prompt
    assert len(prompt) < 3400


def test_audio_prompt_uses_flattened_profile_fields():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Audio intent=late-night breakup song that grows from restraint to direct release." in prompt
    assert "Genre=Synth-Pop." in prompt
    assert "Voice=solo female, airy and emotional." in prompt
    assert "Avoid=avoid spectacle clutter." in prompt
    assert "director_brief_intent" not in prompt


def test_audio_prompt_lets_llm_choose_bpm_when_unlocked():
    prompt = audio_planner._audio_prompt(_prompt_plan(bpm=0))
    assert "Target bpm is not fixed." in prompt
    assert "Choose it yourself from genre, songform, and breathing room." in prompt


def test_audio_prompt_surfaces_retry_feedback_for_korean_lyrics_failures():
    prompt = audio_planner._audio_prompt(
        _prompt_plan(
            audio_retry_attempt=1,
            audio_retry_feedback="audio lyrics quality mismatch: expected readable Korean lines",
        )
    )
    assert "Rewrite attempt 2." in prompt
    assert "Previous issue: audio lyrics quality mismatch: expected readable Korean lines." in prompt
    assert "Every non-empty lyric line must contain readable Hangul words." in prompt
    assert "Do not output any English-only lyric lines." in prompt



def test_audio_prompt_surfaces_retry_feedback_for_pre_chorus_vs_chorus_contrast_failures():
    prompt = audio_planner._audio_prompt(
        _prompt_plan(
            language="en",
            audio_retry_attempt=1,
            audio_retry_feedback="audio lyrics quality mismatch: Pre-Chorus phrasing is too broad compared with Chorus",
        )
    )
    assert "Rewrite attempt 2." in prompt
    assert "Pre-Chorus lines must stay shorter and tighter than Chorus lines." in prompt
    assert "Keep Pre-Chorus average visible length at least a few characters below Chorus average." in prompt
    assert "If the contrast is at risk, shorten Pre-Chorus and make Chorus a little broader instead of opening Pre-Chorus." in prompt
    assert "Make Chorus lines more open and hook-led than Pre-Chorus." in prompt



def test_audio_prompt_surfaces_retry_feedback_for_section_role_underdelivery():
    prompt = audio_planner._audio_prompt(
        _prompt_plan(
            language="ko",
            audio_retry_attempt=1,
            audio_retry_feedback="audio lyrics quality mismatch: Pre-Chorus underdelivers its section role",
        )
    )
    assert "Rewrite attempt 2." in prompt
    assert "Keep every required section at its locked line count; do not shorten or omit required lines." in prompt
    assert "Pre-Chorus must contain at least three compact build-up lyric lines." in prompt



def test_audio_prompt_requires_final_chorus_minimum_matching_its_extended_bar_budget():
    prompt = audio_planner._audio_prompt(_prompt_plan())

    assert "Final Chorus<= 5" in prompt
    assert "Final Chorus>= 5" in prompt



def test_audio_retry_feedback_for_final_chorus_underuse_demands_full_extended_return():
    prompt = audio_planner._audio_prompt(
        _prompt_plan(
            audio_retry_attempt=1,
            audio_retry_feedback="audio lyrics quality mismatch: Final Chorus underuses its extended bar space",
        )
    )

    assert "Final Chorus has the extended bar lane; write five lyric lines for it." in prompt
    assert "Do not shorten Final Chorus to a four-line ordinary chorus." in prompt



def test_audio_outline_rejects_pre_chorus_below_section_role_minimum():
    plan = _prompt_plan()
    outline = {
        "bpm": 108,
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "role": "set", "change": "enter", "line_count": 4},
            {"section": "pre_chorus", "label": "Pre-Chorus", "role": "build", "change": "tighten", "line_count": 2},
            {"section": "chorus", "label": "Chorus", "role": "release", "change": "open", "line_count": 4},
        ],
    }

    with pytest.raises(RuntimeError, match="line_count underdelivers section role for Pre-Chorus"):
        audio_planner._validate_outline_line_budgets(plan, outline)



def test_audio_lyrics_draft_prompt_explicitly_demands_tighter_pre_chorus_than_chorus():
    outline = {
        "lyrics_blocks": [
            {"section": "pre_chorus", "label": "Pre-Chorus", "role": "tighten", "change": "build", "line_count": 3},
            {"section": "chorus", "label": "Chorus", "role": "release", "change": "open", "line_count": 4},
        ]
    }
    prompt = audio_planner._audio_lyrics_draft_prompt(_prompt_plan(language="en"), outline)
    assert "Pre-Chorus lines should stay shorter on average than Chorus lines." in prompt
    assert "Keep Pre-Chorus average visible length safely below Chorus average; do not write long sentence-shaped Pre-Chorus lines." in prompt
    assert "Let Chorus carry the broader release phrasing and the more open hook." in prompt



def test_audio_lyrics_block_prompt_makes_pre_chorus_margin_operational():
    outline = {
        "lyrics_blocks": [
            {"section": "pre_chorus", "label": "Pre-Chorus", "role": "tighten", "change": "build", "line_count": 3},
            {"section": "chorus", "label": "Chorus", "role": "release", "change": "open", "line_count": 4},
        ]
    }
    prompt = audio_planner._audio_lyrics_block_prompt(
        _prompt_plan(language="en", section_bars={"pre_chorus": 8, "chorus": 8}),
        outline,
        [],
        outline["lyrics_blocks"][0],
    )
    assert "Keep this Pre-Chorus visibly shorter per line than the Chorus target." in prompt
    assert "Avoid long sentence-shaped build-up lines here." in prompt



def test_audio_lyrics_draft_prompt_surfaces_retry_feedback_for_korean_lyrics_failures():
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "chorus", "label": "Chorus", "style": "release", "line_count": 4},
        ]
    }
    prompt = audio_planner._audio_lyrics_draft_prompt(
        _prompt_plan(
            audio_retry_attempt=1,
            audio_retry_feedback="audio lyrics quality mismatch: expected readable Korean lines",
        ),
        outline,
    )
    assert "Rewrite attempt 2." in prompt
    assert "Every non-empty lyric line must contain readable Hangul words." in prompt
    assert "Do not output any English-only lyric lines." in prompt



def test_audio_lyrics_draft_prompt_includes_exact_ordered_header_template_for_bridge_runs():
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "role": "setup", "change": "establish", "line_count": 4},
            {"section": "pre_chorus", "label": "Pre-Chorus", "role": "tighten", "change": "build", "line_count": 3},
            {"section": "chorus", "label": "Chorus", "role": "release", "change": "open", "line_count": 4},
            {"section": "verse_2", "label": "Verse 2", "role": "develop", "change": "shift", "line_count": 4},
            {"section": "bridge", "label": "Bridge", "role": "turn", "change": "reframe", "line_count": 2},
            {"section": "chorus", "label": "Final Chorus", "role": "resolve", "change": "payoff", "line_count": 5},
        ]
    }
    prompt = audio_planner._audio_lyrics_draft_prompt(_prompt_plan(language="en"), outline)
    assert "Output this exact header sequence once, in this exact order:" in prompt
    assert "[Verse 1]\n[Pre-Chorus]\n[Chorus]\n[Verse 2]\n[Bridge]\n[Final Chorus]" in prompt
    assert "Do not rename or merge headers; keep [Bridge] exactly as [Bridge]." in prompt


def test_hook_scoring_prefers_world_anchored_korean_hook_over_generic_english():
    plan = _prompt_plan(hook_english_fragments=["all night", "call my name"])
    korean = {"fragment": "새벽 너머", "language_mode": "primary_only", "placement": "chorus"}
    english = {"fragment": "all night", "language_mode": "mixed_language", "placement": "chorus"}
    assert audio_planner._score_hook_candidate(korean, plan) > audio_planner._score_hook_candidate(english, plan)


def test_hook_scoring_penalizes_generic_slogan_like_fragments():
    plan = _prompt_plan(audio_direction="late-night breakup song about remaining light and walking forward")
    anchored = {"fragment": "남은 불빛", "language_mode": "primary_only", "placement": "chorus"}
    generic = {"fragment": "run it back", "language_mode": "mixed_language", "placement": "chorus"}
    assert audio_planner._score_hook_candidate(anchored, plan) > audio_planner._score_hook_candidate(generic, plan)


def test_fallback_hook_state_uses_japanese_hook_when_language_is_ja():
    out = audio_planner._fallback_hook_state(_prompt_plan(language="ja", hook_english_fragments=[]))
    assert out["selected_hook_candidate"]["fragment"] == "残る灯り"


def test_build_audio_plan_accepts_minimal_profile_directly(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "Synth-Pop: glossy synth layers, tight electronic drums, and a solo female vocal with an airy emotional tone.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 불빛", "느린 한숨", "빈 도로", "남은 이름"]},
                {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["조금 가까이", "숨이 차올라", "문이 열려"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["젖은 거리 끝에서", "나는 너를 봐", "사라지지 않아", "끝까지 나아가"]},
                {"section": "bridge", "label": "Bridge", "style": "reframe", "lines": ["멈춘 것 같은 밤", "다시 한 번 숨을 쉬어"]},
                {"section": "chorus", "label": "Final Chorus", "style": "answer", "lines": ["젖은 거리 끝에서", "이제 나를 봐", "흔들리지 않아", "끝까지 나아가", "새벽까지 이어 가"]},
            ],
        },
    )
    cfg = {
        "prompt": "late-night breakup song that grows from restraint to direct release",
        "genre": "synth pop",
        "voice": "solo female, airy and emotional",
        "language": "ko",
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["language"] == "ko"
    assert plan["genre_head"] == "synth pop"
    assert plan["vocal_profile"] == "solo female"
    assert plan["vocal_tone"] == "airy and emotional"
    assert plan["audio_direction"] == "late-night breakup song that grows from restraint to direct release"


def test_build_audio_plan_uses_concept_text_as_genre_hint_fallback(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "Synthwave: pulsing analog pads, driving bass arpeggios, and a glossy nocturnal lead vocal.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["Midnight signs blur", "the highway glows", "my hands stay steady", "the city leans in"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["I drive through the afterglow", "all the lights stay open", "you fade into the skyline", "I keep moving forward"]},
            ],
        },
    )
    cfg = {
        "concept_text": "dreamy synthwave neon highway night drive",
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["language"] == "en"
    assert plan["genre_head"] == "synthwave"
    assert plan["audio_direction"] == cfg["concept_text"]


def test_build_audio_plan_infers_japanese_for_city_pop_when_language_missing(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "City Pop: warm electric piano, soft bass groove, and bittersweet lead vocal over neon-night drums.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["濡れた灯り", "遅い吐息", "空いた道", "残る名前"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["濡れた街の果て", "私は君を見る", "消えはしない", "最後まで進む"]},
            ],
        },
    )
    cfg = {
        "concept_text": "summer boulevard cassette romance under ocean-blue dusk",
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["language"] == "ja"


def test_audio_fixed_fields_do_not_force_japanese_when_language_is_blank():
    assert audio_planner._audio_fixed_fields({"language": ""})["language"] == ""


def test_build_audio_plan_treats_blank_audio_language_as_unset_and_still_infers_from_concept(monkeypatch):
    seen = {}

    def _fake_plan_with_llm(_config, plan):
        seen["prompt_language"] = plan["language"]
        return {
            "genre_description": "Synthwave: pulsing analog pads, driving bass arpeggios, and a glossy nocturnal lead vocal.",
            "bpm": 112,
            "keyscale": "D minor",
            "seed": 41,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["Streetlight flickers", "Rearview ghosts", "Midnight breathing", "Stay with me"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["Drive through the blue", "Hold to the glow", "Nothing is over", "We still move"]},
            ],
        }

    monkeypatch.setattr(audio_planner, "_plan_with_llm", _fake_plan_with_llm)
    cfg = {
        "concept_text": "dreamy synthwave night drive with lonely neon romance",
        "audio": {"language": ""},
    }

    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})

    assert seen["prompt_language"] == "en"
    assert plan["language"] == "en"


def test_build_audio_plan_prefers_audio_brief_over_concept_text(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "City Pop: warm electric piano, soft bass groove, and bittersweet lead vocal over neon-night drums.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["濡れた灯り", "遅い吐息", "空いた道", "残る名前"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["濡れた街の果て", "私は君を見る", "消えはしない", "最後まで進む"]},
            ],
        },
    )
    cfg = {
        "concept_text": "visual-only panel-safe concept",
        "audio": {"brief": "music-facing brief", "hook_brief": "short title-worthy hook", "language": "ja"},
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["audio_direction"] == "music-facing brief"
    assert plan["hook_brief"] == "short title-worthy hook"


def test_build_audio_plan_uses_audio_brief_as_hook_fallback_when_hook_brief_missing(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "City Pop: warm electric piano, soft bass groove, and bittersweet lead vocal over neon-night drums.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["濡れた灯り", "遅い吐息", "空いた道", "残る名前"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["濡れた街の果て", "私は君を見る", "消えはしない", "最後まで進む"]},
            ],
        },
    )
    cfg = {
        "concept_text": "visual-only panel-safe concept",
        "audio": {"brief": "music-facing brief", "language": "ja"},
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["audio_direction"] == "music-facing brief"
    assert plan["hook_brief"] == "music-facing brief"

def test_plan_lyrics_with_llm_runs_final_review_polish(monkeypatch):
    outline = {
        "genre_description": "City Pop: warm electric piano and soft bass.",
        "bpm": 98,
        "keyscale": "A major",
        "seed": 31,
        "duration": 168,
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "role": "set", "change": "enter", "line_count": 4},
            {"section": "chorus", "label": "Chorus", "style": "release", "role": "open", "change": "lift", "line_count": 4},
        ],
    }
    draft = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["古い灯り", "遅い吐息", "空いた道", "残る名前"]},
        {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["まだ行ける", "夜はほどける", "君のいない街でも", "光の方へ進む"]},
    ]
    polished = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["古い灯り", "遅い吐息", "空いた道", "残る名前"]},
        {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["まだ行ける", "夜はほどける", "君のいない街でも", "朝へ向かって進む"]},
    ]
    monkeypatch.setattr(audio_planner, "_generate_lyrics_draft", lambda _config, _plan, _outline: draft)
    monkeypatch.setattr(audio_planner, "_polish_lyrics_sections", lambda _config, _plan, _outline, blocks: polished)
    merged = audio_planner._plan_lyrics_with_llm({}, {"bar_lane": "chorus 8"}, outline)
    chorus = next(row for row in merged["lyrics_blocks"] if row["label"] == "Chorus")
    assert chorus["lines"][-1] == "朝へ向かって進む"


def test_validate_outline_line_budgets_rejects_overpacked_blocks():
    with pytest.raises(RuntimeError, match="line_count too dense for Chorus"):
        audio_planner._validate_outline_line_budgets(
            {"line_budgets": {"Chorus": 6}},
            {"bpm": 108, "lyrics_blocks": [{"label": "Chorus", "line_count": 8}]},
        )


def test_validate_outline_labels_rejects_duplicate_final_chorus():
    with pytest.raises(RuntimeError, match="Final Chorus may appear only once"):
        audio_planner._validate_outline_labels(
            {
                "lyrics_blocks": [
                    {"section": "chorus", "label": "Chorus", "role": "state the hook", "change": "opens up", "line_count": 4},
                    {"section": "chorus", "label": "Final Chorus", "role": "deliver the answer", "change": "gets bigger", "line_count": 4},
                    {"section": "chorus", "label": "Final Chorus", "role": "repeat the answer", "change": "stays big", "line_count": 4},
                ]
            }
        )


def test_validate_outline_labels_requires_final_chorus_to_be_last_chorus_family_block():
    with pytest.raises(RuntimeError, match="Final Chorus must be the last chorus-family block"):
        audio_planner._validate_outline_labels(
            {
                "lyrics_blocks": [
                    {"section": "chorus", "label": "Final Chorus", "role": "deliver the answer", "change": "gets bigger", "line_count": 4},
                    {"section": "chorus", "label": "Chorus 2", "role": "restate the hook", "change": "widens", "line_count": 4},
                ]
            }
        )


def test_normalize_audio_outline_canonicalizes_repeated_section_labels():
    out = audio_planner._normalize_audio_outline(
        {
            "genre_description": "City Pop: warm electric piano and soft bass.",
            "bpm": 102,
            "keyscale": "E major",
            "seed": 31,
            "duration": 172,
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "instrumental", "role": "open", "change": "start", "line_count": 0},
                {"section": "verse_1", "label": "Verse", "style": "narrative", "role": "set", "change": "enter", "line_count": 5},
                {"section": "pre_chorus", "label": "Pre", "style": "lift", "role": "raise", "change": "tighten", "line_count": 3},
                {"section": "chorus", "label": "Chorus", "style": "hook", "role": "land", "change": "open", "line_count": 5},
                {"section": "verse_2", "label": "Verse", "style": "develop", "role": "shift", "change": "deepen", "line_count": 5},
                {"section": "pre_chorus", "label": "Pre", "style": "lift", "role": "raise again", "change": "sharpen", "line_count": 3},
                {"section": "chorus", "label": "Chorus", "style": "hook", "role": "return", "change": "grow", "line_count": 5},
                {"section": "bridge", "label": "Bridge", "style": "contrast", "role": "reframe", "change": "strip back", "line_count": 3},
                {"section": "chorus", "label": "Chorus", "style": "hook", "role": "resolve", "change": "settle", "line_count": 5},
                {"section": "outro", "label": "Outro", "style": "instrumental", "role": "fade", "change": "release", "line_count": 0},
            ],
        }
    )
    assert [row["label"] for row in out["lyrics_blocks"]] == [
        "Intro",
        "Verse 1",
        "Pre-Chorus",
        "Chorus",
        "Verse 2",
        "Pre-Chorus 2",
        "Chorus 2",
        "Bridge",
        "Final Chorus",
        "Outro",
    ]


def test_validate_outline_line_budgets_rejects_overcrowded_short_form_songform():
    with pytest.raises(RuntimeError, match="short-form outline too crowded"):
        audio_planner._validate_outline_line_budgets(
            {"duration_max_sec": 180, "line_budgets": {"Intro": 0, "Verse 1": 5, "Pre-Chorus": 3, "Chorus": 5, "Post-Chorus": 2, "Verse 2": 5, "Pre-Chorus 2": 3, "Chorus 2": 5, "Bridge": 3, "Final Chorus": 5, "Outro": 0}},
            {
                "bpm": 110,
                "lyrics_blocks": [
                    {"label": "Intro", "line_count": 0},
                    {"label": "Verse 1", "line_count": 5},
                    {"label": "Pre-Chorus", "line_count": 3},
                    {"label": "Chorus", "line_count": 5},
                    {"label": "Post-Chorus", "line_count": 2},
                    {"label": "Verse 2", "line_count": 5},
                    {"label": "Pre-Chorus 2", "line_count": 3},
                    {"label": "Chorus 2", "line_count": 5},
                    {"label": "Bridge", "line_count": 3},
                    {"label": "Final Chorus", "line_count": 5},
                    {"label": "Outro", "line_count": 0},
                ],
            },
        )


def test_generate_lyrics_block_skips_llm_for_zero_line_intro():
    block = {"section": "intro", "label": "Intro", "style": "open", "line_count": 0}
    out = audio_planner._generate_lyrics_block({}, _prompt_plan(), {"lyrics_blocks": [block]}, [], block)
    assert out["lines"] == []


def test_parse_audio_lyrics_draft_allows_omitted_zero_line_outro_header():
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "outro", "label": "Outro", "style": "tail", "line_count": 0},
        ]
    }
    drafted = "\n".join(
        [
            "[Verse 1]",
            "젖은 유리 위로 밤이 번져",
            "늦은 숨결만 손끝에 남아",
        ]
    )

    out = audio_planner._parse_audio_lyrics_draft(outline, drafted)

    assert out == [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 유리 위로 밤이 번져", "늦은 숨결만 손끝에 남아"]},
        {"section": "outro", "label": "Outro", "style": "tail", "lines": []},
    ]



def test_parse_audio_lyrics_draft_allows_omitted_zero_line_outro_header_before_end_tag():
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "outro", "label": "Outro", "style": "tail", "line_count": 0},
        ]
    }
    drafted = "\n".join(
        [
            "[Verse 1]",
            "젖은 유리 위로 밤이 번져",
            "늦은 숨결만 손끝에 남아",
            "[end]",
        ]
    )

    out = audio_planner._parse_audio_lyrics_draft(outline, drafted)

    assert out == [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 유리 위로 밤이 번져", "늦은 숨결만 손끝에 남아"]},
        {"section": "outro", "label": "Outro", "style": "tail", "lines": []},
    ]



def test_generate_lyrics_draft_parses_full_song_and_only_rewrites_invalid_block(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "chorus", "label": "Chorus", "style": "release", "line_count": 4},
            {"section": "chorus", "label": "Final Chorus", "style": "answer", "line_count": 4},
        ]
    }
    drafted = "\n".join(
        [
            "[Verse 1]",
            "젖은 유리 위로 밤이 번져",
            "늦은 숨결만 손끝에 남아",
            "[Chorus]",
            "밤을 건너 네게 가",
            "남은 불빛이 반짝여",
            "도시의 끝이 열려",
            "오늘 밤 숨이 차올라",
            "[Final Chorus]",
            "밤을 건너 네게 가",
            "남은 불빛이 반짝여",
            "도시의 끝이 열려",
            "오늘 밤 숨이 차올라",
        ]
    )

    monkeypatch.setattr(audio_planner, "generate_text", lambda _config, _prompt: drafted)
    called: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block):
        called.append(str(block.get("label", "")).strip())
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["밤을 지나 내가 가", "남은 불빛 끝에 서", "도시의 문이 열려", "오늘 밤 내가 간다"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block", _rewrite)
    monkeypatch.setattr(audio_planner, "_polish_lyrics_sections", lambda _config, _plan, _outline, blocks: blocks)
    out = audio_planner._generate_lyrics_draft({}, _prompt_plan(), outline)
    assert [row["label"] for row in out] == ["Verse 1", "Chorus", "Final Chorus"]
    assert called == ["Final Chorus"]
    assert out[-1]["lines"] == ["밤을 지나 내가 가", "남은 불빛 끝에 서", "도시의 문이 열려", "오늘 밤 내가 간다"]


def test_refresh_overused_imagery_rewrites_late_blocks_only(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "verse_2", "label": "Verse 2", "style": "change", "line_count": 2},
            {"section": "bridge", "label": "Bridge", "style": "reframe", "line_count": 2},
        ]
    }
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 불빛 아래 서 있어", "번진 유리 끝을 바라봐"]},
        {"section": "verse_2", "label": "Verse 2", "style": "change", "lines": ["젖은 불빛 속을 다시 가", "번진 유리 앞에 또 서"]},
        {"section": "bridge", "label": "Bridge", "style": "reframe", "lines": ["젖은 불빛이 멀어져", "번진 유리 대신 숨을 쉬어"]},
    ]
    rewritten_labels: list[str] = []
    revision_notes: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        rewritten_labels.append(str(block.get("label", "")).strip())
        revision_notes.append(revision_note)
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["마른 새벽 쪽으로 걸어", "꺼진 골목 뒤로 숨을 쉬어"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._refresh_overused_imagery({}, _prompt_plan(), outline, blocks)
    assert rewritten_labels == ["Verse 2", "Bridge"]
    assert any("Do not invent a brand-new place, prop, or scene object" in note for note in revision_notes)
    assert any("젖은" in note and "불빛" in note for note in revision_notes)
    assert out[0]["lines"] == ["젖은 불빛 아래 서 있어", "번진 유리 끝을 바라봐"]
    assert out[1]["lines"] == ["마른 새벽 쪽으로 걸어", "꺼진 골목 뒤로 숨을 쉬어"]


def test_refresh_hook_fit_rewrites_korean_chorus_with_disconnected_english_fragment(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "style": "release", "line_count": 4},
            {"section": "chorus", "label": "Final Chorus", "style": "answer", "line_count": 4},
        ]
    }
    plan = _prompt_plan(
        selected_hook_candidate={"fragment": "남은 불빛"},
        hook_english_fragments=["run it back"],
        language="ko",
    )
    blocks = [
        {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["run it back, 심장이 먼저 알아", "네가 없는데도 난 네 쪽을 봐", "비에 씻겨 가게", "같은 상처를 돌아"]},
        {"section": "chorus", "label": "Final Chorus", "style": "answer", "lines": ["남은 불빛 따라, 난 앞으로 가", "젖은 밤도 지나", "내 숨을 켜", "혼자도 걸어가"]},
    ]
    rewritten: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        rewritten.append(str(block.get("label", "")).strip())
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["남은 불빛 아래", "내 발끝이 먼저 가", "지워진 밤을 지나", "나는 앞으로 가"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._refresh_hook_fit({}, plan, outline, blocks)
    assert rewritten == ["Chorus"]
    assert out[0]["lines"] == ["남은 불빛 아래", "내 발끝이 먼저 가", "지워진 밤을 지나", "나는 앞으로 가"]


def test_refresh_hook_fit_rewrites_japanese_chorus_without_selected_hook(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "style": "release", "line_count": 4},
            {"section": "chorus", "label": "Final Chorus", "style": "answer", "line_count": 4},
        ]
    }
    plan = _prompt_plan(
        language="ja",
        selected_hook_candidate={"fragment": "残る灯り"},
        hook_english_fragments=[],
    )
    blocks = [
        {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["窓の外で波が揺れる", "夏の影がまだ残る", "君の気配が遠く光る", "夜明け前に息をのむ"]},
        {"section": "chorus", "label": "Final Chorus", "style": "answer", "lines": ["残る灯りだけを見つめ", "この夜を抜けていく", "濡れた道はほどけていく", "もう迷わず進める"]},
    ]
    rewritten: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        rewritten.append(str(block.get("label", "")).strip())
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["残る灯りが胸に揺れる", "波の匂いを追いかける", "君のいない道を抜けて", "夜明け前へ走り出す"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._refresh_hook_fit({}, plan, outline, blocks)
    assert rewritten == ["Chorus"]
    assert out[0]["lines"][0] == "残る灯りが胸に揺れる"


def test_polish_lyrics_sections_rewrites_only_llm_targets(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "bridge", "label": "Bridge", "style": "reframe", "line_count": 2},
            {"section": "chorus", "label": "Final Chorus", "style": "answer", "line_count": 2},
        ]
    }
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 밤을 걷고", "이름을 지워"]},
        {"section": "bridge", "label": "Bridge", "style": "reframe", "lines": ["끝을 본다", "다시 간다"]},
        {"section": "chorus", "label": "Final Chorus", "style": "answer", "lines": ["남은 불빛 아래", "앞으로 간다"]},
    ]
    monkeypatch.setattr(
        audio_planner,
        "_plan_lyrics_rewrite_targets_with_llm",
        lambda _config, _plan, _blocks: [{"label": "Bridge", "reason": "make the reframe feel more specific"}],
    )
    rewritten: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        rewritten.append(str(block.get("label", "")).strip())
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["끝이 나서 보이는 길", "나는 그 길로 다시 가"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._polish_lyrics_sections({}, _prompt_plan(), outline, blocks)
    assert rewritten == ["Bridge"]
    assert out[0]["lines"] == ["젖은 밤을 걷고", "이름을 지워"]
    assert out[1]["lines"] == ["끝이 나서 보이는 길", "나는 그 길로 다시 가"]


def test_polish_lyrics_sections_can_handle_artist_style_targets(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "final_chorus", "label": "Final Chorus", "style": "answer", "line_count": 2},
        ]
    }
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 밤을 걷고", "이름을 지워"]},
        {"section": "final_chorus", "label": "Final Chorus", "style": "answer", "lines": ["남은 불빛 아래", "앞으로 간다"]},
    ]
    monkeypatch.setattr(
        audio_planner,
        "_plan_lyrics_rewrite_targets_with_llm",
        lambda _config, _plan, _blocks: [{"label": "Final Chorus", "reason": "make the payoff feel more personal and less generic"}],
    )
    rewritten: list[str] = []

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        rewritten.append(str(block.get("label", "")).strip())
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["남은 불빛 끝에서", "이제 난 내 이름으로 가"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._polish_lyrics_sections({}, _prompt_plan(), outline, blocks)
    assert rewritten == ["Final Chorus"]
    assert out[0]["lines"] == ["젖은 밤을 걷고", "이름을 지워"]
    assert out[1]["lines"] == ["남은 불빛 끝에서", "이제 난 내 이름으로 가"]



def test_polish_lyrics_sections_reinforces_pre_chorus_vs_chorus_contrast_when_rewriting_pre_chorus(monkeypatch):
    outline = {
        "lyrics_blocks": [
            {"section": "verse_1", "label": "Verse 1", "style": "restraint", "line_count": 2},
            {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "line_count": 3},
            {"section": "chorus", "label": "Chorus", "style": "release", "line_count": 4},
        ]
    }
    blocks = [
        {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 밤을 걷고", "숨을 고른다"]},
        {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["조금 더 가까이 가", "말들이 길어져 가", "밤이 천천히 열린다"]},
        {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["지금 너를 불러", "더 크게 열어", "밤 끝까지 가", "심장이 뛴다"]},
    ]
    monkeypatch.setattr(
        audio_planner,
        "_plan_lyrics_rewrite_targets_with_llm",
        lambda _config, _plan, _blocks: [{"label": "Pre-Chorus", "reason": "tighten bar-fit and sharpen the lift into chorus"}],
    )
    seen = {}

    def _rewrite(_config, _plan, _outline, completed, block, revision_note):
        seen["label"] = str(block.get("label", "")).strip()
        seen["revision_note"] = revision_note
        return {
            "section": str(block.get("section", "")).strip(),
            "label": str(block.get("label", "")).strip(),
            "style": str(block.get("style", "")).strip(),
            "lines": ["조금 더 가까이", "숨이 더 짧아져", "바로 문을 열어"],
        }

    monkeypatch.setattr(audio_planner, "_generate_lyrics_block_with_note", _rewrite)
    out = audio_planner._polish_lyrics_sections({}, _prompt_plan(language="en"), outline, blocks)
    assert seen["label"] == "Pre-Chorus"
    assert "Pre-Chorus should stay tighter than the Chorus" in seen["revision_note"]
    assert "Do not let it open broader than the Chorus payoff" in seen["revision_note"]
    assert out[1]["lines"] == ["조금 더 가까이", "숨이 더 짧아져", "바로 문을 열어"]


def test_normalize_and_validate_keeps_llm_generated_bpm_and_keyscale(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "Rock: distorted electric guitars, punchy live drums, and a raw vocal that rises into a bigger hook.",
            "bpm": 146,
            "keyscale": "E minor",
            "seed": 31,
            "duration": 180,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "drive", "lines": ["붉은 불꽃", "거친 숨결", "뜨거운 심장", "깨어난 밤"]},
                {"section": "pre_chorus", "label": "Pre-Chorus", "style": "lift", "lines": ["더 크게 울려", "멈추지 않아", "문을 열어"]},
                {"section": "chorus", "label": "Chorus", "style": "impact", "lines": ["지금 뛰어", "끝까지 가", "모든 걸 태워", "나를 외쳐"]},
                {"section": "bridge", "label": "Bridge", "style": "drop", "lines": ["정적이 와", "다시 깨어"]},
                {"section": "chorus", "label": "Final Chorus", "style": "impact", "lines": ["지금 뛰어", "두려움 없이", "벽을 넘어", "나를 외쳐"]},
            ],
        },
    )
    out = audio_planner._normalize_and_validate({}, _prompt_plan(bpm=108, keyscale="A major"))
    assert out["bpm"] == 146
    assert out["keyscale"] == "E minor"
