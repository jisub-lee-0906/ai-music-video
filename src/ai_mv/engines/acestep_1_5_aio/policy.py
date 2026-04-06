from __future__ import annotations

from collections.abc import Sequence

DEFAULT_BEATS_PER_BAR = 4
DEFAULT_DURATION_BPM = 120
DEFAULT_ENDING_MODE = "clean_resolve"
DEFAULT_ENDING_VOCAL_DENSITY = "medium"
DEFAULT_TERMINAL_END_TAG = True
DEFAULT_ENDING_TAGS: dict[str, list[str]] = {
    "hard_stop": ["clean ending", "hard stop", "decisive final hit"],
    "clean_resolve": ["clean ending", "resolved final lift"],
    "glow_fade": ["clean ending", "gentle synth tail", "soft afterglow"],
    "bittersweet_tail": ["clean ending", "brief emotional tail", "controlled after-image"],
    "anthem_lift": ["clean ending", "anthemic final lift", "open final release"],
}
DEFAULT_LINE_BUDGETS: dict[str, int] = {
    "Intro": 0,
    "Verse 1": 6,
    "Verse 2": 6,
    "Pre-Chorus": 4,
    "Pre-Chorus 2": 4,
    "Chorus": 6,
    "Chorus 2": 6,
    "Final Chorus": 6,
    "Post-Chorus": 3,
    "Bridge": 4,
    "Outro": 0,
}
DEFAULT_SECTION_BARS: dict[str, int] = {
    "intro": 4,
    "verse": 12,
    "verse_1": 12,
    "verse_2": 12,
    "pre_chorus": 8,
    "chorus": 12,
    "post_chorus": 4,
    "bridge": 8,
    "outro": 4,
    "final_chorus_bonus": 4,
}
PREFERRED_SONGFORM: tuple[tuple[str, str], ...] = (
    ("intro", "Intro"),
    ("verse_1", "Verse 1"),
    ("pre_chorus", "Pre-Chorus"),
    ("chorus", "Chorus"),
    ("post_chorus", "Post-Chorus"),
    ("verse_2", "Verse 2"),
    ("pre_chorus", "Pre-Chorus 2"),
    ("chorus", "Chorus 2"),
    ("bridge", "Bridge"),
    ("chorus", "Final Chorus"),
    ("outro", "Outro"),
)


def audio_policy(config: dict) -> dict:
    audio = _audio_config(config)
    bpm = _coerce_positive_int(audio.get("bpm"), default=0)
    beats_per_bar = _coerce_positive_int(audio.get("beats_per_bar"), default=DEFAULT_BEATS_PER_BAR)
    section_bars = resolve_section_bars(audio)
    override_duration = _explicit_target_duration(audio)
    preferred_rows = preferred_songform_rows()
    duration = int(override_duration) if override_duration is not None else 0
    return {
        "duration": int(duration),
        "duration_override": override_duration is not None,
        "bar_lane": bar_lane_summary(preferred_rows, section_bars),
        "beats_per_bar": beats_per_bar,
        "section_bars": section_bars,
        "seed": int(audio.get("seed", 31)),
        "bpm": bpm,
        "quality": str(audio.get("quality", "V0")),
        "keyscale": str(audio.get("keyscale", "")).strip(),
        "ending_mode": _ending_mode(audio),
        "terminal_end_tag": _terminal_end_tag(audio),
        "final_chorus_required": _coerce_bool(audio.get("final_chorus_required"), default=True),
        "outro_required": _coerce_bool(audio.get("outro_required"), default=False),
        "ending_vocal_density": _ending_vocal_density(audio),
        "ending_tags": _ending_tags(audio),
        "line_budgets": resolve_line_budgets(audio),
    }


def preferred_songform_rows() -> list[dict[str, str]]:
    return [{"section": sec, "label": label} for sec, label in PREFERRED_SONGFORM]


def compute_duration_from_blocks(blocks: Sequence[dict], bpm: int, beats_per_bar: int, section_bars: dict[str, int]) -> int:
    rows = _rows(blocks)
    if not rows:
        return compute_duration_from_rows(preferred_songform_rows(), bpm, beats_per_bar, section_bars)
    bars = section_bar_plan(rows, section_bars)
    return _bars_to_seconds(sum(bars), bpm, beats_per_bar)


def compute_duration_from_rows(rows: Sequence[dict], bpm: int, beats_per_bar: int, section_bars: dict[str, int]) -> int:
    bars = section_bar_plan(_rows(rows), section_bars)
    return _bars_to_seconds(sum(bars), bpm, beats_per_bar)


def compute_section_windows(
    duration_sec: float,
    rows: Sequence[dict],
    bpm: int,
    beats_per_bar: int,
    section_bars: dict[str, int] | None,
) -> list[dict]:
    normalized_rows = _rows(rows)
    if not normalized_rows:
        raise RuntimeError("lyrics_blocks empty after validation")
    bars = section_bar_plan(normalized_rows, section_bars or DEFAULT_SECTION_BARS)
    total_bars = sum(bars)
    if total_bars <= 0:
        raise RuntimeError("invalid section bar plan")
    out: list[dict] = []
    cursor = 0.0
    for idx, (row, section_bar_count) in enumerate(zip(normalized_rows, bars)):
        seg = float(duration_sec) * (float(section_bar_count) / float(total_bars))
        end = float(duration_sec) if idx == len(normalized_rows) - 1 else min(float(duration_sec), cursor + seg)
        out.append(
            {
                "name": str(row.get("section", "section")).strip().lower(),
                "label": str(row.get("label", "")).strip() or str(row.get("section", "section")).strip().lower(),
                "start_sec": round(cursor, 3),
                "end_sec": round(end, 3),
            }
        )
        cursor = end
    return out


def resolve_section_bars(audio: dict) -> dict[str, int]:
    raw = audio.get("section_bars", {}) if isinstance(audio, dict) else {}
    if raw in ("", None):
        return dict(DEFAULT_SECTION_BARS)
    if not isinstance(raw, dict):
        raise RuntimeError("audio.section_bars must be a mapping")
    resolved = dict(DEFAULT_SECTION_BARS)
    for key, value in raw.items():
        name = str(key).strip().lower()
        if not name:
            continue
        resolved[name] = _coerce_positive_int(value, default=0, label=f"audio.section_bars.{name}")
    return resolved


def resolve_line_budgets(audio: dict) -> dict[str, int]:
    resolved = dict(DEFAULT_LINE_BUDGETS)
    language = str(audio.get("language", "")).strip().lower()
    ending_mode = _ending_mode(audio)
    terminal_end_tag = _terminal_end_tag(audio)
    ending_vocal_density = _ending_vocal_density(audio)
    outro_required = _coerce_bool(audio.get("outro_required"), default=False)
    if language == "ko":
        resolved["Verse 1"] = 4
        resolved["Verse 2"] = 4
        resolved["Pre-Chorus"] = 3
        resolved["Pre-Chorus 2"] = 3
        resolved["Chorus"] = 4
        resolved["Chorus 2"] = 4
        resolved["Final Chorus"] = 4
        resolved["Bridge"] = 2
        resolved["Intro"] = 0
        resolved["Outro"] = 0
    if ending_mode == "clean_resolve":
        resolved["Intro"] = min(int(resolved.get("Intro", 0)), 0)
    if outro_required and terminal_end_tag and ending_mode == "clean_resolve":
        resolved["Outro"] = min(int(resolved.get("Outro", 0)), 0)
    return resolved


def section_bar_plan(rows: Sequence[dict], section_bars: dict[str, int]) -> list[int]:
    normalized_rows = _rows(rows)
    if not normalized_rows:
        return []
    out: list[int] = []
    last_chorus_idx = _last_chorus_index(normalized_rows)
    for idx, row in enumerate(normalized_rows):
        section = str(row.get("section", "")).strip().lower()
        label = str(row.get("label", "")).strip().lower()
        bars = _base_bar_count(section, section_bars)
        if section == "chorus" and idx == last_chorus_idx and "final chorus" in label:
            if int(section_bars.get("final_chorus", 0)) > 0:
                bars = int(section_bars["final_chorus"])
            else:
                bars += int(section_bars.get("final_chorus_bonus", 0))
        out.append(max(1, int(bars)))
    return out


def bar_lane_summary(rows: Sequence[dict], section_bars: dict[str, int]) -> str:
    normalized_rows = _rows(rows)
    bars = section_bar_plan(normalized_rows, section_bars)
    compact: list[str] = []
    for row, count in zip(normalized_rows, bars):
        section = str(row.get("section", "")).strip().lower()
        label = str(row.get("label", "")).strip().lower()
        if section == "chorus" and "final chorus" in label:
            compact.append(f"final chorus {count}")
            continue
        compact.append(f"{_lane_name(section)} {count}")
    return ", ".join(compact)


def _explicit_target_duration(audio: dict) -> int | None:
    raw = audio.get("target_duration_sec") if isinstance(audio, dict) else None
    if raw in ("", None):
        return None
    return _coerce_positive_int(raw, default=0, label="audio.target_duration_sec")


def _bars_to_seconds(total_bars: int, bpm: int, beats_per_bar: int) -> int:
    resolved_bpm = int(bpm) if int(bpm) > 0 else DEFAULT_DURATION_BPM
    resolved_beats = int(beats_per_bar) if int(beats_per_bar) > 0 else DEFAULT_BEATS_PER_BAR
    seconds = float(total_bars) * float(resolved_beats) * 60.0 / float(resolved_bpm)
    return max(1, int(round(seconds)))


def _base_bar_count(section: str, section_bars: dict[str, int]) -> int:
    if section in section_bars:
        return int(section_bars[section])
    if section.startswith("verse_") and "verse" in section_bars:
        return int(section_bars["verse"])
    if section == "chorus" and "final_chorus" in section_bars:
        return int(section_bars["chorus"])
    return int(DEFAULT_SECTION_BARS.get(section, DEFAULT_SECTION_BARS.get("verse", 12)))


def _lane_name(section: str) -> str:
    aliases = {
        "verse_1": "verse 1",
        "verse_2": "verse 2",
        "pre_chorus": "pre",
        "post_chorus": "post",
    }
    return aliases.get(section, section.replace("_", " "))


def _last_chorus_index(rows: Sequence[dict]) -> int:
    indexes = [idx for idx, row in enumerate(rows) if str(row.get("section", "")).strip().lower() == "chorus"]
    return indexes[-1] if indexes else -1


def _rows(rows: Sequence[dict]) -> list[dict]:
    return [dict(row) for row in rows if isinstance(row, dict)]


def _coerce_positive_int(raw: object, default: int, label: str = "") -> int:
    if raw in ("", None):
        return int(default)
    try:
        value = int(raw)
    except Exception as exc:  # pragma: no cover - defensive conversion guard
        if label:
            raise RuntimeError(f"{label} must be an integer") from exc
        return int(default)
    if value <= 0:
        if label:
            raise RuntimeError(f"{label} must be > 0")
        return int(default)
    return value


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _ending_mode(audio: dict) -> str:
    raw = str(audio.get("ending_mode", DEFAULT_ENDING_MODE)).strip().lower()
    allowed = {"hard_stop", "clean_resolve", "glow_fade", "bittersweet_tail", "anthem_lift"}
    return raw if raw in allowed else DEFAULT_ENDING_MODE


def _terminal_end_tag(audio: dict) -> bool:
    return _coerce_bool(audio.get("terminal_end_tag"), default=DEFAULT_TERMINAL_END_TAG)

def _ending_vocal_density(audio: dict) -> str:
    raw = str(audio.get("ending_vocal_density", DEFAULT_ENDING_VOCAL_DENSITY)).strip().lower()
    allowed = {"full", "medium", "low", "tail_only"}
    return raw if raw in allowed else DEFAULT_ENDING_VOCAL_DENSITY


def _ending_tags(audio: dict) -> list[str]:
    raw = audio.get("ending_tags", []) if isinstance(audio, dict) else []
    if isinstance(raw, list):
        vals = [str(item).strip() for item in raw if str(item).strip()]
        if vals:
            return vals
    return list(DEFAULT_ENDING_TAGS[_ending_mode(audio)])


def _coerce_bool(raw: object, default: bool) -> bool:
    if raw in ("", None):
        return bool(default)
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)
