from __future__ import annotations


def compact_sentences(text: object, limit: int = 1) -> str:
    raw = " ".join(str(text).replace("\n", " ").split()).strip()
    if not raw:
        return ""
    parts = [part.strip(" .") for part in raw.split(".") if part.strip(" .")]
    if not parts:
        return ""
    return ". ".join(parts[: max(1, limit)])


def compact_series(text: object, limit: int = 6) -> str:
    vals = [part.strip(" .") for part in str(text).replace(";", ",").split(",")]
    out = [part for part in vals if part]
    return ", ".join(out[: max(1, limit)])


def audio_digest(data: dict, sentence_limit: int = 2) -> str:
    parts = [
        compact_sentences(data.get("audio_direction", ""), sentence_limit),
        compact_sentences(data.get("genre_description", ""), sentence_limit),
    ]
    return join_nonempty(parts, ". ")


def profile_digest(data: dict, sentence_limit: int = 1) -> str:
    return compact_sentences(data.get("profile_summary", ""), sentence_limit)


def visual_digest(data: dict, sentence_limit: int = 2) -> str:
    return compact_sentences(data.get("visual_direction", ""), sentence_limit)


def negative_digest(data: dict, sentence_limit: int = 1) -> str:
    return compact_sentences(data.get("negative_direction", ""), sentence_limit)


def style_digest(data: dict, sentence_limit: int = 2) -> str:
    return compact_sentences(data.get("style_guidance", ""), sentence_limit)


def lyrics_digest(text: object, limit: int = 8, line_limit: int = 120) -> str:
    lines = [line.strip()[:line_limit] for line in str(text).splitlines() if line.strip()]
    return " | ".join(lines[: max(1, limit)])


def section_digest(sections: list[dict]) -> str:
    rows: list[str] = []
    for row in sections:
        name = str(row.get("name", "section")).strip()
        start = round(float(row.get("start_sec", row.get("start", 0.0))), 2)
        end = round(float(row.get("end_sec", row.get("end", 0.0))), 2)
        rows.append(f"{name}:{start}-{end}")
    return ", ".join(rows)


def label_digest(sections: list[dict]) -> str:
    labels = [str(row.get("label", row.get("name", "section"))).strip() for row in sections]
    return ", ".join(label for label in labels if label)


def join_nonempty(parts: list[str], sep: str = ". ") -> str:
    vals = [part.strip() for part in parts if str(part).strip()]
    return sep.join(vals)
