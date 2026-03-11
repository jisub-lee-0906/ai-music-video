from __future__ import annotations

from ai_mv.core.profile_brief import build_profile_brief
from ai_mv.core.contracts.prompt_normalize import normalize_audio_fields, validate_audio_lyrics_language
from ai_mv.core.contracts.prompt_schema import audio_schema
from ai_mv.engines.acestep_1_5_split.policy import audio_policy
from ai_mv.infra.codex_cli_client import generate_structured


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = _audio_config(config)
    tags = _audio_tags(audio)
    guidance = _style_guidance(config)
    profile = build_profile_brief(tags, guidance)
    plan = {
        "tags": tags,
        "style_guidance": guidance,
        "language": _audio_language(audio),
        "filename_prefix": f"artifacts/runs_state/{payload['run_id']}/audio/music",
    }
    plan.update(profile)
    plan.update(audio_policy(config))
    return _plan_with_quality_attempts(config, plan)


def _plan_with_llm(config: dict, plan: dict) -> dict:
    prompt = _audio_prompt(plan)
    return generate_structured(config, prompt, audio_schema())


def _audio_prompt(plan: dict) -> str:
    tags = str(plan["tags"]).strip()
    guidance = str(plan["style_guidance"]).strip()
    tags_clause = f"Input tags={tags}. " if tags else ""
    guidance_clause = f"Style guidance={guidance}. " if guidance else ""
    language_clause = _language_clause(plan)
    profile_clause = _profile_clause(plan)
    bpm_clause = _target_bpm_clause(plan)
    seed_clause = f"Creative seed={int(plan.get('seed', 31))}. "
    return _audio_prompt_rules() + (
        f"Target duration={int(plan['duration'])} sec. "
        f"{bpm_clause}{seed_clause}{tags_clause}{guidance_clause}{language_clause}{profile_clause}"
    )


def _audio_prompt_rules() -> str:
    return _audio_structure_rules() + _audio_form_rules() + _audio_description_rules()


def _audio_structure_rules() -> str:
    return (
        "You are an elite songwriter-producer. Return JSON only. "
        "No markdown. No prose outside JSON. "
        "Required top-level keys: genre_description,bpm,keyscale,seed,duration,lyrics_blocks. "
        "Required lyrics_blocks item keys: section,label,style,lines. "
        "Allowed section values only: intro,verse_1,verse_2,pre_chorus,chorus,post_chorus,bridge,outro. "
        "Composition target must follow input reference strictly. "
        "Design aggressive section contrast with distinct diction per section. "
        "Give each section a clearly different job in the emotional arc so the song feels staged and cumulative. "
        "Intro should open atmosphere with minimal language and immediate tone-setting. "
        "Intro should stay sparse and usually fit in 2-3 short lines unless the style strongly demands more. "
        "Verse: forward motion, clear imagery, memorable cadence, and strong lyrical specificity. "
        "Verse should include concrete sensory or scene details without copying examples, and should advance the scene rather than summarizing emotion. "
        "Prefer fuller line density in verses than in pre-chorus or outro. "
        "Keep line endings clear and singable; avoid vague filler. "
        "Pre-chorus: emotional lift, tension, breath-space, smoother vowel flow and intimacy, with language that clearly prepares a release. "
        "Pre-chorus should feel slightly more open and less crowded than the verse. "
        "Pre-chorus usually works best in 2-3 concise lines unless the song clearly needs an extra pickup line. "
        "Chorus: high-impact hook, chant-ready phrasing, immediate recall, strong emotional release, and the clearest central idea of the song. "
        "Chorus should simplify language compared with the verse so the hook lands instantly. "
        "Post-chorus: very short callback lines built around the same hook phrase, acting as a lingering afterglow rather than a new verse. "
        "Bridge should create a genuine contrast in perspective, energy, or emotional framing before the final return, and should redirect or thin the language instead of stacking more imagery. "
        "Bridge should usually be sparser than the verse and should not feel lyrically crowded. "
    )


def _audio_form_rules() -> str:
    return (
        "Target a complete pop song arc rather than a fragment. "
        "Preferred block order is intro, verse_1, pre_chorus, chorus, post_chorus, verse_2, pre_chorus, chorus, bridge, chorus, outro. "
        "If duration forces compression, keep at minimum intro, verse_1, pre_chorus, chorus, verse_2, bridge, final chorus, outro. "
        "A bridge must never be the final large section; it must be followed by another chorus block. "
        "Use repeated chorus blocks when the song returns, and label the last one as Final Chorus while keeping section='chorus'. "
        "Keep the first line of each chorus in the same hook family so recall stays immediate. "
        "If a second chorus appears before the bridge, keep the same hook family but change at least one support line and one payoff/callback line so it does not read as an exact duplicate. "
        "The final chorus must feel bigger than the first chorus by adding payoff, lift, or a fresh line turn instead of simple copy-paste. "
        "The final chorus should preserve the hook opening but introduce at least two new lines or one new image turn that was not used in the first chorus. "
        "At least half of the non-opening lines in the final chorus should differ from the first chorus. "
        "Use the bridge as the setup for the final chorus payoff, so the final chorus answers or releases the bridge tension. "
        "The final chorus should contain one concrete visual or emotional payoff line that sounds like the line listeners wait for. "
        "Do not repeat the exact same six chorus lines three times across the song. "
        "Verse_2 must advance the scene or relationship, not paraphrase verse_1. "
        "Post-chorus should usually stay at 2-3 very short lines and behave like an echo, not a new verse. "
        "Aim for 9-11 lyrics_blocks for a full song whenever duration allows. "
    )


def _audio_description_rules() -> str:
    return (
        "genre_description must be one compact production paragraph including arrangement cues "
        "(808/bass, synth layers, harmonies, transitions, impact), in 2-3 sentences only. "
        "genre_description is written directly into the AceStep tags text field, so it must stay plain production language with no bullets, labels, or markdown. "
        "genre_description must explicitly cover groove foundation, lead vocal character, and hook instrumentation. "
        "genre_description should also describe pocket, rhythm feel, or timing character in concrete production terms when relevant. "
        "Mention at least one clear groove behavior such as bounce, glide, pulse, sway, swing, push, or restraint. "
        "Prefer tangible musical language like swing, bounce, pulse, breath, glide, shimmer, punch, or restraint over generic adjectives. "
        "Prefer one coherent production identity instead of mixing many genres. "
        "Keep genre_description reusable as a downstream audio-direction brief, not a poetic review. "
        "For each block, lines must be 2-4 short singable lines with concrete imagery and cadence. "
        "Only chorus may expand beyond 4 lines when needed for hook repetition or chant response. "
        "Prefer vivid action verbs and sonic words over abstract statements. "
        "Write lines with clear mouth-feel and internal rhythm suitable for topline melody. "
        "Keep 1-3 recurring concept words or images alive across verse, pre-chorus, and chorus so the song identity stays glued together. "
        "Include one repeatable hook phrase in chorus/post-chorus for recall and repeat it at least twice in chorus lines. "
        "Chorus must include at least one call-and-response or chant-like fragment. "
        "Make the hook phrase title-worthy: short, singable, and easy to remember after one listen. "
        "The hook phrase should usually contain one concrete image, object, place, weather cue, or physical sensation instead of a generic romance placeholder. "
        "Prefer a distinctive hook phrase built from the song's actual world, such as rain, glass, boulevard, headlights, harbor, summer heat, cassette, or neon, rather than generic love-song filler. "
        "Avoid fallback hook language like 'call my name', 'hold me', 'stay with me', 'all night', or repeated hey-oh syllables unless the surrounding line adds a fresh concrete twist. "
        "Avoid using the same generic imperative in multiple chorus lines. "
        "Do not let every chorus line carry the same weight; support lines should set up the hook and payoff lines should feel earned. "
        "Avoid ending the song with a weak comedown if the chorus has not fully paid off yet. "
        "Avoid generic filler and repeated empty slogans. "
        "Treat profile_summary, audio_direction, and hook_direction as the source of truth for genre lane, vocal attitude, and recurring imagery. "
        "When tags grow longer in future profiles, compress them into one coherent producer brief instead of listing every tag back. "
        "Do not invent extra sections or fields. "
    )


def _audio_tags(audio: dict) -> str:
    raw = audio.get("tags", []) if isinstance(audio, dict) else []
    vals = [str(x).strip() for x in raw if str(x).strip()]
    return ", ".join(vals)


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _style_guidance(config: dict) -> str:
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _audio_language(audio: dict) -> str:
    raw = str(audio.get("language", "en")).strip().lower() if isinstance(audio, dict) else "en"
    return raw if raw in {"en", "ja", "ko"} else "en"


def _target_bpm_clause(plan: dict) -> str:
    bpm = int(plan.get("bpm", 0))
    return f"Target bpm={bpm}. " if bpm > 0 else ""


def _language_clause(plan: dict) -> str:
    lang = str(plan.get("language", "")).strip().lower()
    if not lang:
        return ""
    return f"Lyrics language={lang}. "


def _profile_clause(plan: dict) -> str:
    parts = [
        _profile_line("Profile steering", plan.get("profile_summary", "")),
        _profile_line("Audio direction", plan.get("audio_direction", "")),
        _profile_line("Hook direction", plan.get("hook_direction", "")),
        _profile_line("Visual carryover", plan.get("visual_direction", "")),
        _profile_line("Avoid", plan.get("negative_direction", "")),
    ]
    return "".join(parts)


def _profile_line(label: str, text: object) -> str:
    val = str(text).strip()
    return f"{label}={val}. " if val else ""


def _validate_audio_plan_quality(plan: dict) -> None:
    choruses = [x for x in plan.get("lyrics_blocks", []) if str(x.get("section", "")).strip().lower() == "chorus"]
    if len(choruses) < 2:
        return
    _validate_second_chorus(choruses)
    _validate_final_chorus(choruses)


def _validate_second_chorus(choruses: list[dict]) -> None:
    first = _clean_lines(choruses[0])
    second = _clean_lines(choruses[1])
    if first and second and first == second:
        raise RuntimeError("audio planner quality failure: second chorus duplicates first chorus exactly")


def _validate_final_chorus(choruses: list[dict]) -> None:
    first = _clean_lines(choruses[0])
    final_block = choruses[-1]
    final = _clean_lines(final_block)
    label = str(final_block.get("label", "")).strip().lower()
    if len(choruses) >= 3 and "final chorus" not in label:
        raise RuntimeError("audio planner quality failure: final chorus label missing")
    if not _has_final_chorus_payoff(first, final):
        raise RuntimeError("audio planner quality failure: final chorus payoff too weak")


def _has_final_chorus_payoff(first: list[str], final: list[str]) -> bool:
    if not first or not final:
        return False
    if len(final) <= len(first):
        return False
    opening = first[0].lower()
    new_lines = [x for x in final[1:] if x.lower() not in {y.lower() for y in first[1:]}]
    if len(new_lines) >= 2 and final[0].lower() == opening:
        return True
    return False


def _clean_lines(block: dict) -> list[str]:
    lines = block.get("lines", [])
    if not isinstance(lines, list):
        return []
    return [str(x).strip() for x in lines if str(x).strip()]


def _plan_with_quality_attempts(config: dict, plan: dict) -> dict:
    attempts = _planner_attempts(config)
    last: Exception | None = None
    for idx in range(attempts):
        try:
            attempt_plan = _attempt_plan(plan, idx)
            return _normalize_and_validate(config, attempt_plan)
        except RuntimeError as exc:
            last = exc
    raise last if last else RuntimeError("audio planner failed")


def _normalize_and_validate(config: dict, plan: dict) -> dict:
    planned = _plan_with_llm(config, plan)
    normalized = normalize_audio_fields(planned)
    normalized["tags"] = plan["tags"]
    normalized["style_guidance"] = plan["style_guidance"]
    normalized["language"] = plan["language"]
    normalized["profile_summary"] = plan["profile_summary"]
    normalized["audio_direction"] = plan["audio_direction"]
    normalized["hook_direction"] = plan["hook_direction"]
    normalized["visual_direction"] = plan["visual_direction"]
    normalized["negative_direction"] = plan["negative_direction"]
    normalized["filename_prefix"] = plan["filename_prefix"]
    normalized["quality"] = plan["quality"]
    if not str(normalized.get("keyscale", "")).strip():
        normalized["keyscale"] = str(plan.get("keyscale", "")).strip()
    validate_audio_lyrics_language(normalized["lyrics"], plan["language"])
    _validate_audio_plan_quality(normalized)
    return normalized


def _attempt_plan(plan: dict, idx: int) -> dict:
    out = dict(plan)
    out["seed"] = int(plan.get("seed", 31)) + (idx * 1009)
    return out


def _planner_attempts(config: dict) -> int:
    audio = _audio_config(config)
    raw = audio.get("planner_attempts", 3) if isinstance(audio, dict) else 3
    try:
        return max(1, int(raw))
    except Exception:
        return 3
