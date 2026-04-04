# REF Prompt Closure Checklist

## Purpose
This checklist defines when a REF prompt family is considered closed enough to stop exploratory prompting and move on to higher-level MV writing.

## Closure Standard
A family is `closed` only if all of the following are true:

1. The generated image is usable as a music-video keyframe.
2. Background geometry remains literal and stable.
3. The heroine stays singular and identity-stable.
4. The intended event difference is visible in the image, not just in the text.
5. The result is repeatable across at least 2 prompt variants or reruns without collapsing into a different family.

## Current Status

### Closed Or Nearly Closed
- `gate_pass`
  - Reason: entry crossing reads cleanly and stays physically grounded.
- `threshold_crossing / passage_exit`
  - Reason: current passage-exit wording is more literal than doorway framing and behaves more stably.
- `platform_edge / bridge_motion (pressure)`
  - Reason: wet platform edge, yellow tactile line, and footprint trace are readable and stable.
- `platform_edge / final_platform_push (handoff)`
  - Reason: after removing automatic footprint carryover, the same platform world stays intact with a stronger forward step and the track still running beside her.
- `curb_crossing / entry`
  - Current best pattern: left-edge entry into the wet crosswalk with open road ahead.
  - Reason: rerun confirms this creates a distinct crossing event and breaks centered repetition.
- `curb_crossing / continuation`
  - Current best pattern: middle-right crossing continuation to avoid centered reset.
  - Reason: rerun confirms it keeps the crossing alive without collapsing back into a generic frontal walk.
- `curb_crossing / handoff`
  - Current best pattern: right-edge blocking with the open road held to the opposite side.
  - Reason: latest micro-study and sequence rerun show this is more stable than `traffic opening` wording and remains visually distinct from entry and payoff.
- `curb_crossing / payoff`
  - Current best pattern: moving away toward the far curb with more open street surrounding her.
  - Reason: rerun confirms this behaves as a real release/payoff event rather than another forward-walk frame.
- `window_contact`
  - Current best pattern: same heroine + station/window edge + direct metal-frame contact + forward continuation.
  - Reason: latest probe shows actual tactile contact events without collapsing into reflection mood.
- `brace_pause`
  - Current best pattern: same heroine + wet rail + one braced hand + forward line still implied.
  - Reason: latest probe shows a readable brief pause that does not fully collapse into a static fashion pose.

### Partially Closed
- `sidewalk_continuation`
  - Current best pattern: `same heroine + curb line stays tight at her feet + same stride carries forward`
  - Why partial: usable and grounded, but still tends to recenter and can collapse back into generic route walking without stronger sequence context.
- `passage_compression`
  - Current best pattern: `same heroine + right wall of the narrow passage + same stride carrying forward + one hand trails the rail`
  - Why partial: visually strong and usable, but still needs one more in-sequence confirmation before treating it as fully closed.

### Open
- No fully open family is blocking the current profile anymore.

## Current Best Image-Driven Patterns

### Bridge Pressure
- Best shape:
  - `same heroine + wet platform edge + yellow tactile line near feet + crossing or shorter step + optional footprint trail`

### Bridge Handoff / Platform Push
- Best shape:
  - `same heroine + wet platform edge at night + yellow tactile line near feet + track still running beside her + longer forward step`

### Final Chorus Entry
- Best shape:
  - `same heroine + steps in from the left edge of the wet crosswalk + open road stretching ahead`

### Final Chorus Continuation
- Best shape:
  - `same heroine + middle-right side of the wet crosswalk + same stride alive`

### Final Chorus Handoff
- Best shape:
  - `same heroine + right edge of the wet crosswalk + same stride carries forward + open road held to the left`

### Final Chorus Payoff
- Best shape:
  - `same heroine + moves away toward the far curb from the wet crosswalk + more of the open street surrounding her`

## What Counts As Failure
- Background changes to a different world family.
- The heroine recenters into a generic frontal walking image when blocking should differ.
- Event difference exists only in text but not in the image.
- Secondary trace/detail invents duplicate subjects or scene clutter.
- A later variant looks “safe” but visually collapses into the same keyframe role as the previous shot.

## Next Closure Order
1. Close `sidewalk_continuation` by proving it can differ from generic walking across at least one repeated sequence context.
2. Re-open `passage_compression` only if the current profile still needs a stronger non-platform compression event.
3. Run a full-profile sequence check to see whether `sidewalk_continuation` still flattens repeated sections.

## Rule
Do not move on to denser story scripting until the current profile has at least one fully closed release family and one fully closed compression family.
