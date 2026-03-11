from __future__ import annotations

from collections.abc import Iterable

_AUDIO_KEYS = (
    "pop",
    "rock",
    "ballad",
    "city",
    "disco",
    "synth",
    "piano",
    "guitar",
    "bass",
    "string",
    "drum",
    "groove",
    "hook",
    "chorus",
    "harmon",
)
_VOCAL_KEYS = ("vocal", "voice", "falsetto", "solo", "duet", "lead", "whisper", "airy", "gritty")
_VISUAL_KEYS = (
    "neon",
    "night",
    "urban",
    "retro",
    "nostalg",
    "rain",
    "glass",
    "chrome",
    "harbor",
    "boulevard",
    "summer",
    "sunset",
    "street",
    "headlight",
)
_HOOK_KEYS = ("neon", "rain", "glass", "harbor", "boulevard", "chrome", "taxi", "street", "summer", "heat", "cassette")
_MOTION_KEYS = ("bounce", "pulse", "glide", "sway", "swing", "push", "restraint", "lift")
_MOOD_KEYS = ("rom", "warm", "cool", "melanch", "dream", "grace", "eleg", "adult", "night", "polished")
_NEGATIVE_KEYS = ("no ", "avoid ", "without ", "not ", "never ", "non-")


def build_profile_brief(tags: str | Iterable[str], guidance: str) -> dict[str, str]:
    phrases = _phrases(tags, guidance)
    used: set[str] = set()
    audio = _take_matching(phrases, _AUDIO_KEYS, 5, used, ("mood",))
    vocal = _take_matching(phrases, _VOCAL_KEYS, 2, used)
    visual = _take_matching(phrases, _VISUAL_KEYS, 4, used)
    motion = _take_matching(phrases, _MOTION_KEYS, 2, used)
    mood = _take_matching(phrases, _MOOD_KEYS, 3, used)
    hook = _hook_phrase(phrases)
    negative = _negative_brief(phrases)
    return {
        "profile_summary": _profile_summary(audio, vocal, mood, visual),
        "audio_direction": _audio_direction(audio, vocal, motion),
        "hook_direction": _hook_direction(hook, motion, mood),
        "visual_direction": _visual_direction(visual, mood),
        "negative_direction": negative,
    }


def _phrases(tags: str | Iterable[str], guidance: str) -> list[str]:
    merged = _split_text(tags) + _split_text(guidance)
    out: list[str] = []
    seen: set[str] = set()
    for item in merged:
        key = item.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _split_text(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, str):
        text = raw
    else:
        text = ", ".join(str(x).strip() for x in raw if str(x).strip())
    text = text.replace(";", ",").replace("/", ",").replace("|", ",")
    vals = [x.strip(" .") for x in text.split(",")]
    return [x for x in vals if x]


def _take_matching(
    phrases: list[str], keys: tuple[str, ...], limit: int, used: set[str], reject: tuple[str, ...] = ()
) -> str:
    vals: list[str] = []
    for item in phrases:
        low = item.lower()
        if low in used or not _has_any(item, keys) or _has_any(item, reject):
            continue
        used.add(low)
        vals.append(item)
        if len(vals) >= limit:
            break
    return ", ".join(vals)


def _negative_brief(phrases: list[str]) -> str:
    vals = [x for x in phrases if _has_any(x, _NEGATIVE_KEYS)]
    if vals:
        return ", ".join(vals[:4])
    return "avoid profile drift, contradictory genre mashups, and generic placeholder language"


def _profile_summary(audio: str, vocal: str, mood: str, visual: str) -> str:
    parts = [audio, vocal, mood, visual]
    text = _sentence_parts(parts, 3)
    return text or "Use the merged profile as one coherent lane instead of listing tags back."


def _audio_direction(audio: str, vocal: str, motion: str) -> str:
    parts = [audio, vocal, motion]
    text = _sentence_parts(parts, 3)
    return text or "Keep one coherent musical lane, one lead-vocal identity, and one groove behavior."


def _hook_direction(hook: str, motion: str, mood: str) -> str:
    parts = [hook, motion or mood]
    text = _sentence_parts(parts, 2)
    if text:
        return f"Build the hook around this concrete song world: {text}."
    return "Build the hook around one concrete world image, one physical cue, and one repeatable phrase."


def _visual_direction(visual: str, mood: str) -> str:
    parts = [visual, mood]
    text = _sentence_parts(parts, 2)
    return text or "Preserve one readable world, one palette family, and one emotional weather."


def _hook_phrase(phrases: list[str]) -> str:
    vals = [x for x in phrases if _has_any(x, _HOOK_KEYS)]
    return ", ".join(vals[:3])


def _sentence_parts(parts: list[str], limit: int) -> str:
    vals = [x for x in parts if x][:limit]
    return "; ".join(vals)


def _has_any(text: str, keys: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(key in low for key in keys)
