from __future__ import annotations

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "104"


def map_audio_workflow(config: dict, plan: dict) -> dict:
    text_inputs = {
        "tags": _audio_conditioning_text(plan),
        "lyrics": str(plan["lyrics"]),
        "seed": int(plan["seed"]),
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
            AUDIO_KSAMPLER: {"seed": int(plan["seed"])},
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


def _audio_conditioning_text(plan: dict) -> str:
    tags = _split_tags(str(plan.get("tags", "")).strip())
    audio_direction = _trim_sentence(str(plan.get("audio_direction", "")).strip())
    profile_summary = _trim_sentence(str(plan.get("profile_summary", "")).strip())
    desc = _trim_sentence(str(plan.get("genre_description", "")).strip())
    lead = _conditioning_lead(tags, audio_direction, profile_summary)
    if lead and desc:
        return lead if lead == desc else f"{lead}. {desc}"
    return lead or desc


def _trim_sentence(text: str) -> str:
    return str(text).strip().rstrip(". ")


def _split_tags(text: str) -> list[str]:
    vals = [part.strip(" .") for part in str(text).replace(";", ",").split(",")]
    return [part for part in vals if part]


def _audio_tag_spine(tags: list[str]) -> str:
    genre = _pick_tags(tags, ("city pop", "synthpop", "pop", "rock", "ballad", "disco"), 1)
    instruments = _pick_tags(tags, ("electric piano", "chorus guitar", "analog synth", "synth pad", "fretless bass", "string", "drum"), 4)
    vocal = _pick_tags(tags, ("female solo vocal", "male solo vocal", "solo vocal", "lead vocal", "vocal"), 2)
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
    detailed = _join_sentences(audio_direction)
    if len(detailed.split()) >= 8:
        return detailed
    if len(spine.split()) >= 5:
        return spine
    return _sentenceize(audio_direction or profile_summary or spine)


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


def _join_sentences(*parts: str) -> str:
    vals = [_sentenceize(part) for part in parts if _sentenceize(part)]
    if not vals:
        return ""
    return ". ".join(vals)
