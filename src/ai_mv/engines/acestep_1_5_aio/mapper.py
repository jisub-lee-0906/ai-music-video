from __future__ import annotations

import zlib

from ai_mv.core.prompt_digests import compact_sentences, compact_series

AUDIO_TEXT = "94"
AUDIO_LATENT = "98"
AUDIO_KSAMPLER = "3"
AUDIO_SAVE = "107"

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
    "j pop": "J-Pop",
    "j rock": "J-Rock",
    "jpop": "J-Pop",
    "jrock": "J-Rock",
    "jazz": "Jazz",
    "jazz fusion": "Jazz Fusion",
    "k pop": "K-Pop",
    "k rock": "K-Rock",
    "kpop": "K-Pop",
    "krock": "K-Rock",
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
    desc = compact_sentences(plan.get("genre_description", ""), 2)
    genre = _genre_label(tags, desc)
    body = _trim_sentence(desc)
    if genre and body:
        prefix = f"{genre}:"
        if body.lower().startswith(prefix.lower()):
            return body
        compact = _dedupe_genre_prefix(body, genre)
        return f"{prefix} {compact}".strip()
    return body or genre


def _dedupe_genre_prefix(body: str, genre: str) -> str:
    trimmed = _trim_sentence(body)
    head = _trim_sentence(genre).lower()
    parts = trimmed.split(":", 1)
    if len(parts) == 2 and _normalize_genre_label(parts[0]) == genre:
        return parts[1].strip()
    if trimmed.lower().startswith(f"{head} "):
        return trimmed[len(genre) :].strip(" :")
    return trimmed


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
    if low in GENRE_ALIASES:
        return GENRE_ALIASES[low]
    parts = [part for part in low.split(" / ") if part]
    return "/".join(_normalize_genre_segment(part) for part in parts if part)


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


def _normalize_genre_token(word: str) -> str:
    if not word:
        return ""
    if word in UPPERCASE_WORDS:
        return word.upper()
    if len(word) <= 3 and word.isalpha() and word not in GENRE_STOPWORDS:
        return word.upper()
    return word.capitalize()


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
