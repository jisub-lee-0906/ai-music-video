from __future__ import annotations

import zlib

from ai_mv.core.prompt_digests import compact_sentences, compact_series

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "104"


def map_audio_workflow(config: dict, plan: dict) -> dict:
    seed = _audio_seed(plan)
    text_inputs = {
        "tags": _audio_conditioning_text(plan),
        "lyrics": str(plan["lyrics"]),
        "seed": seed,
        "bpm": int(plan["bpm"]),
        "duration": int(plan["duration"]),
        "language": _audio_language(plan),
    }
    keyscale = str(plan.get("keyscale", "")).strip()
    if keyscale:
        text_inputs["keyscale"] = keyscale
    return {
        "node.inputs": {
            AUDIO_TEXT: text_inputs,
            AUDIO_LATENT: {"seconds": int(plan["duration"])},
            AUDIO_KSAMPLER: {"seed": seed},
            AUDIO_SAVE: {
                "filename_prefix": str(plan["filename_prefix"]),
                "quality": str(plan["quality"]),
            },
        }
    }


def audio_required_inputs() -> dict[str, list[str]]:
    return {
        "TextEncodeAceStepAudio1.5": ["tags", "lyrics", "seed", "bpm", "duration", "language"],
        "EmptyAceStep1.5LatentAudio": ["seconds"],
        "KSampler": ["seed"],
        "SaveAudioMP3": ["filename_prefix", "quality"],
    }


def _audio_language(plan: dict) -> str:
    raw = str(plan.get("language", "en")).strip().lower()
    return raw if raw in {"en", "ja", "ko"} else "en"


def _audio_seed(plan: dict) -> int:
    base = int(plan.get("seed", 0))
    variant = str(plan.get("filename_prefix", "")).strip()
    retry = int(plan.get("retry", 0))
    text = f"{base}|{variant}|{retry}".encode("utf-8")
    return 4000 + int(zlib.crc32(text) % 1_000_000)


def _audio_conditioning_text(plan: dict) -> str:
    tags = _split_tags(str(plan.get("tags", "")).strip())
    audio_direction = compact_sentences(plan.get("audio_direction", ""), 1)
    profile_summary = compact_sentences(plan.get("profile_summary", ""), 1)
    desc = compact_sentences(plan.get("genre_description", ""), 2)
    lead = _conditioning_lead(tags, audio_direction, profile_summary)
    desc = _novel_desc(desc, lead)
    if lead and desc:
        return f"{lead}. {desc}"
    return lead or desc


def _trim_sentence(text: str) -> str:
    return str(text).strip().rstrip(". ")


def _split_tags(text: str) -> list[str]:
    vals = [part.strip(" .") for part in compact_series(text, 20).split(",")]
    return [part for part in vals if part]


def _audio_tag_spine(tags: list[str]) -> str:
    genre = _pick_tags(tags, ("city pop", "synthpop", "pop", "rock", "ballad", "disco", "r&b", "neo soul", "hip hop", "dance"), 1)
    instruments = _pick_tags(tags, ("electric piano", "chorus guitar", "analog synth", "synth pad", "fretless bass", "string", "drum", "bass", "guitar", "keys"), 4)
    vocal = _pick_tags(tags, ("female solo vocal", "male solo vocal", "solo vocal", "lead vocal", "vocal"), 1)
    groove = _pick_tags(tags, ("bounce", "glide", "swing", "pulse", "groove", "lift"), 2)
    tail = _dedupe_tags(instruments + vocal + groove)
    if not genre and not tail:
        return ""
    head = genre[0] if genre else tail.pop(0)
    if not tail:
        return _sentenceize(head)
    return _sentenceize(f"{head} with {_join_series(tail)}")


def _conditioning_lead(tags: list[str], audio_direction: str, profile_summary: str) -> str:
    spine = _audio_tag_spine(tags)
    if spine:
        return spine
    if audio_direction:
        return _sentenceize(audio_direction)
    return _sentenceize(profile_summary or "")


def _pick_tags(tags: list[str], keys: tuple[str, ...], limit: int = 3) -> list[str]:
    out: list[str] = []
    for tag in tags:
        low = tag.lower()
        if any(key in low for key in keys) and tag not in out:
            out.append(tag)
        if len(out) >= limit:
            break
    return out


def _dedupe_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def _join_series(parts: list[str], conj: str = "and") -> str:
    vals = [_sentenceize(part) for part in parts if part]
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    if len(vals) == 2:
        return f"{vals[0]} {conj} {vals[1]}"
    return f"{', '.join(vals[:-1])}, {conj} {vals[-1]}"


def _sentenceize(text: str) -> str:
    cleaned = _trim_sentence(text).replace(";", ",")
    return " ".join(cleaned.split())


def _novel_desc(desc: str, lead: str) -> str:
    if not desc:
        return ""
    parts = [part.strip(" .") for part in str(desc).split(".") if part.strip(" .")]
    if not lead:
        return ". ".join(parts[:2])
    lead_words = _signal_words(lead)
    ranked = sorted(parts, key=lambda part: (_overlap_ratio(_signal_words(part), lead_words), len(part)))
    best = ranked[0] if ranked else ""
    return _sentenceize(best)


def _signal_words(text: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "the",
        "with",
        "for",
        "into",
        "that",
        "this",
        "from",
        "then",
        "over",
        "under",
        "should",
        "keep",
        "make",
        "feel",
        "more",
        "less",
    }
    words = []
    for raw in str(text).lower().replace("-", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) > 2 and token not in stop:
            words.append(token)
    return set(words)


def _overlap_ratio(words: set[str], base: set[str]) -> float:
    if not words or not base:
        return 0.0
    return len(words & base) / max(1, len(words))
