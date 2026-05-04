from __future__ import annotations

import zlib
import re

from ai_mv.core.prompt_digests import compact_sentences, compact_series

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "104"

GENRE_ALIASES = {
    "aor": "AOR",
    "afrobeat": "Afrobeat",
    "afrobeats": "Afrobeats",
    "alt pop": "Alt Pop",
    "alt rock": "Alt Rock",
    "alternative pop": "Alternative Pop",
    "alternative rock": "Alternative Rock",
    "ambient": "Ambient",
    "amapiano": "Amapiano",
    "ballad": "Ballad",
    "bluegrass": "Bluegrass",
    "blues": "Blues",
    "boom bap": "Boom Bap",
    "bossa nova": "Bossa Nova",
    "breakbeat": "Breakbeat",
    "city pop": "City Pop",
    "country": "Country",
    "dance": "Dance",
    "dance pop": "Dance Pop",
    "dancehall": "Dancehall",
    "deep house": "Deep House",
    "disco": "Disco",
    "dnb": "Drum and Bass",
    "drill": "Drill",
    "drum and bass": "Drum and Bass",
    "dub": "Dub",
    "dubstep": "Dubstep",
    "edm": "EDM",
    "electro": "Electro",
    "electro pop": "Electro Pop",
    "electropop": "Electro Pop",
    "electronic": "Electronic",
    "emo": "Emo",
    "folk": "Folk",
    "funk": "Funk",
    "future bass": "Future Bass",
    "garage": "Garage",
    "gospel": "Gospel",
    "grunge": "Grunge",
    "hard rock": "Hard Rock",
    "hardcore": "Hardcore",
    "hip hop": "Hip-Hop",
    "hip-hop": "Hip-Hop",
    "house": "House",
    "hyperpop": "Hyperpop",
    "indie folk": "Indie Folk",
    "indie pop": "Indie Pop",
    "indie rock": "Indie Rock",
    "jazz": "Jazz",
    "jazz fusion": "Jazz Fusion",
    "latin pop": "Latin Pop",
    "lo fi": "Lo-Fi",
    "lofi": "Lo-Fi",
    "metal": "Metal",
    "neo soul": "Neo-Soul",
    "new jack swing": "New Jack Swing",
    "phonk": "Phonk",
    "pop": "Pop",
    "pop punk": "Pop Punk",
    "pop rock": "Pop Rock",
    "post punk": "Post-Punk",
    "progressive house": "Progressive House",
    "progressive rock": "Progressive Rock",
    "punk": "Punk",
    "punk rock": "Punk Rock",
    "r and b": "R&B",
    "r&b": "R&B",
    "rap": "Rap",
    "reggae": "Reggae",
    "reggaeton": "Reggaeton",
    "retro pop": "Retro Pop",
    "rock": "Rock",
    "shoegaze": "Shoegaze",
    "singer songwriter": "Singer-Songwriter",
    "soul": "Soul",
    "synth pop": "Synth Pop",
    "synthwave": "Synthwave",
    "techno": "Techno",
    "trance": "Trance",
    "trap": "Trap",
    "trip hop": "Trip-Hop",
    "uk garage": "UK Garage",
    "vaporwave": "Vaporwave",
}
GENRE_HINTS = tuple(
    {
        *GENRE_ALIASES.keys(),
        "acoustic",
        "adult contemporary",
        "chill",
        "club",
        "fusion",
        "house",
        "instrumental",
        "orchestral",
        "orchestra",
        "soulful",
        "swing",
        "wave",
    }
)
GENRE_STOPWORDS = {"a", "an", "and", "for", "of", "the"}
UPPERCASE_WORDS = {"aor", "edm", "idm", "uk", "us", "dj", "r&b"}


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
    _copy_optional_audio_controls(
        text_inputs,
        plan,
        {
            "timesignature",
            "generate_audio_codes",
            "cfg_scale",
            "temperature",
            "top_p",
            "top_k",
            "min_p",
        },
    )
    return {
        "node.inputs": {
            AUDIO_TEXT: text_inputs,
            AUDIO_LATENT: {"seconds": int(plan["duration"])},
            AUDIO_KSAMPLER: _audio_sampler_inputs(plan, seed),
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


def _copy_optional_audio_controls(target: dict, plan: dict, keys: set[str]) -> None:
    for key in keys:
        if key in plan and plan[key] not in (None, ""):
            target[key] = plan[key]


def _audio_sampler_inputs(plan: dict, seed: int) -> dict:
    out = {"seed": seed}
    mapping = {
        "sampler_steps": "steps",
        "sampler_cfg": "cfg",
        "sampler_name": "sampler_name",
        "scheduler": "scheduler",
    }
    for source, dest in mapping.items():
        if source not in plan or plan[source] in (None, ""):
            continue
        value = plan[source]
        if source == "sampler_steps" and not _positive_number(value):
            continue
        if source == "sampler_cfg" and not _positive_number(value):
            continue
        out[dest] = value
    return out


def _positive_number(value: object) -> bool:
    try:
        return float(value) > 0.0
    except Exception:
        return False


def _audio_language(plan: dict) -> str:
    raw = str(plan.get("language", "")).strip().lower()
    return raw if raw in {"en", "ja", "ko"} else ""


def _audio_seed(plan: dict) -> int:
    base = int(plan.get("seed", 0))
    variant = str(plan.get("filename_prefix", "")).strip()
    retry = int(plan.get("retry", 0))
    text = f"{base}|{variant}|{retry}".encode("utf-8")
    return 4000 + int(zlib.crc32(text) % 1_000_000)


def _audio_conditioning_text(plan: dict) -> str:
    workflow_tags = _workflow_acestep_tags(plan)
    if workflow_tags:
        return workflow_tags
    raise RuntimeError("missing acestep workflow prompt")


def _workflow_acestep_tags(plan: dict) -> str:
    prompts = plan.get("workflow_prompts") if isinstance(plan, dict) else {}
    payload = prompts.get("acestep") if isinstance(prompts, dict) else {}
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("tags", "")).strip()


def _locked_audio_contract(plan: dict) -> dict:
    vocal_profile = _normalize_vocal_profile(str(plan.get("vocal_profile", "")).strip())
    vocal_tone = _normalize_vocal_tone(str(plan.get("vocal_tone", "")).strip())
    if vocal_profile.lower() == vocal_tone.lower():
        vocal_tone = ""
    return {
        "genre_head": _normalize_genre_label(str(plan.get("genre_head", "")).strip()),
        "vocal_profile": vocal_profile,
        "vocal_tone": vocal_tone,
    }


def _dedupe_genre_prefix(body: str, genre: str) -> str:
    trimmed = _trim_sentence(body)
    head = _trim_sentence(genre).lower()
    parts = trimmed.split(":", 1)
    if len(parts) == 2:
        normalized_prefix = _normalize_genre_label(parts[0])
        if normalized_prefix:
            if normalized_prefix == genre:
                return parts[1].strip()
            return parts[1].strip()
    if trimmed.lower().startswith(f"{head} "):
        return trimmed[len(genre) :].strip(" :")
    return trimmed


def _trim_sentence(text: str) -> str:
    return str(text).strip().rstrip(". ")


def _normalize_vocal_profile(text: str) -> str:
    return _trim_sentence(text)


def _normalize_vocal_tone(text: str) -> str:
    return _trim_sentence(text)


def _merge_locked_vocal_contract(body: str, locked_vocal: str, locked_tone: str) -> str:
    compact = _trim_sentence(body)
    clauses = [part.strip() for part in compact.split(",") if part.strip()]
    filtered = [part for part in clauses if not _matches_locked_vocal_clause(part, locked_vocal, locked_tone)]
    prefix: list[str] = []
    if locked_vocal:
        prefix.append(locked_vocal)
    if locked_tone and not _contains_clause(filtered, locked_tone):
        prefix.append(locked_tone)
    if prefix and filtered:
        return ", ".join([*prefix, *filtered])
    if prefix:
        return ", ".join(prefix)
    return compact


def _contains_clause(clauses: list[str], target: str) -> bool:
    needle = _trim_sentence(target).lower()
    return any(_trim_sentence(part).lower() == needle for part in clauses)


def _matches_locked_vocal_clause(text: str, locked_vocal: str, locked_tone: str) -> bool:
    low = _trim_sentence(text).lower()
    if not low:
        return False
    vocal = _trim_sentence(locked_vocal).lower()
    tone = _trim_sentence(locked_tone).lower()
    if vocal and low == vocal:
        return True
    if tone and low == tone:
        return True
    if vocal and vocal in low:
        if not tone or tone in low:
            return True
    if tone and tone in low and _looks_like_vocal_clause(low):
        return True
    return _looks_like_vocal_clause(low)


def _looks_like_vocal_clause(text: str) -> bool:
    low = _trim_sentence(text).lower()
    if not low:
        return False
    patterns = (
        r"\bvocal\b",
        r"\bvocals\b",
        r"\bvoice\b",
        r"\blead vocal\b",
        r"\blead vocals\b",
        r"\blead singer\b",
        r"\btopline\b",
        r"\btop line\b",
        r"\bfemale lead\b",
        r"\bmale lead\b",
        r"\bfemale solo\b",
        r"\bmale solo\b",
    )
    return any(re.search(pattern, low) for pattern in patterns)


def _split_tags(text: str) -> list[str]:
    vals = [part.strip(" .") for part in compact_series(text, 20).split(",")]
    return [part for part in vals if part]

def _genre_label(tags: list[str], desc: str) -> str:
    candidates = _genre_candidates(tags)
    for tag in candidates:
        label = _normalize_genre_label(tag)
        if label:
            return label
    if ":" in desc:
        head = desc.split(":", 1)[0]
        return _normalize_genre_label(head)
    return ""


def _normalize_genre_label(text: str) -> str:
    cleaned = _sentenceize(text).strip(" ,.")
    if not cleaned:
        return ""
    low = cleaned.lower().replace("_", " ").replace("/", " / ")
    low = " ".join(low.split())
    if any(sep in low for sep in (" ", "-", "/")) and low not in GENRE_ALIASES:
        direct = _normalize_explicit_genre_phrase(low)
        if direct:
            return direct
    embedded = _embedded_genre_alias(low)
    if embedded:
        return embedded
    if low in GENRE_ALIASES:
        return GENRE_ALIASES[low]
    parts = [part for part in low.split(" / ") if part]
    return "/".join(_normalize_genre_segment(part) for part in parts if part)


def _embedded_genre_alias(text: str) -> str:
    padded = f" {text} "
    for alias in sorted(GENRE_ALIASES.keys(), key=len, reverse=True):
        needle = f" {alias} "
        if needle in padded:
            return GENRE_ALIASES[alias]
    return ""


def _genre_candidates(tags: list[str]) -> list[str]:
    preferred = [tag for tag in tags if _looks_like_genre(tag)]
    return preferred or tags


def _looks_like_genre(text: str) -> bool:
    normalized = " ".join(_sentenceize(text).lower().replace("_", " ").replace("-", " ").split())
    if normalized in GENRE_ALIASES:
        return True
    return any(hint in normalized for hint in GENRE_HINTS)


def _normalize_genre_segment(text: str) -> str:
    words = [word for word in text.split() if word]
    out: list[str] = []
    for raw in words:
        word = raw.strip(" ,.")
        if not word:
            continue
        if word in UPPERCASE_WORDS:
            out.append(word.upper())
            continue
        if word in GENRE_STOPWORDS:
            out.append(word)
            continue
        if "-" in word:
            pieces = [_normalize_genre_token(piece) for piece in word.split("-") if piece]
            out.append("-".join(pieces))
            continue
        out.append(_normalize_genre_token(word))
    return " ".join(out)


def _normalize_explicit_genre_phrase(text: str) -> str:
    parts = []
    for raw in text.replace("/", " / ").split():
        if raw == "/":
            parts.append("/")
            continue
        normalized = GENRE_ALIASES.get(raw, "")
        if normalized:
            parts.append(normalized)
            continue
        if raw in GENRE_STOPWORDS:
            parts.append(raw)
            continue
        if "-" in raw:
            pieces = [_normalize_genre_token(piece) for piece in raw.split("-") if piece]
            parts.append("-".join(pieces))
            continue
        parts.append(_normalize_genre_token(raw))
    compact = " ".join(parts).replace(" / ", "/").strip()
    return compact


def _normalize_genre_token(word: str) -> str:
    if not word:
        return ""
    if word in UPPERCASE_WORDS:
        return word.upper()
    if len(word) <= 3 and word.isalpha() and word not in GENRE_STOPWORDS:
        return word.upper()
    return word.capitalize()

def _sentenceize(text: str) -> str:
    cleaned = _trim_sentence(text).replace(";", ",")
    return " ".join(cleaned.split())
