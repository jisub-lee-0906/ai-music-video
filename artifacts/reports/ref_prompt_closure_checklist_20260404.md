# REF Prompt Closure Checklist

## Purpose
This checklist defines when a REF prompt family is considered closed and stable enough to stop exploratory prompting and move on to higher-level MV writing.

## Closure Standard
A family is `closed` only if all of the following are true:

1. The generated image is usable as a music-video keyframe.
2. Background geometry remains literal and stable.
3. The heroine stays singular and identity-stable.
4. The intended event difference is visible in the image, not just in the text.
5. The result is repeatable across at least 2 prompt variants or reruns without collapsing into a different family.

## Current Status

### Closed
- `gate_pass`
  - Reason: entry crossing reads cleanly and stays physically grounded.
- `threshold_crossing / passage_exit`
  - Reason: current passage-exit wording is more literal than doorway framing and behaves more stably.
- `platform_edge / bridge_motion (pressure)`
  - Reason: wet platform edge, yellow tactile line, and footprint trace are readable and stable.
- `platform_edge / final_platform_push (handoff)`
  - Reason: after removing automatic footprint carryover, the same platform world stays intact with a stronger forward step and the track still running beside her.
- `curb_crossing / entry`
  - Current best pattern: far-left edge entry into the wet crosswalk with most of the road left open ahead.
  - Reason: latest blocking rerun confirms this is the most stable way to break centered repetition and make entry read as a real crossing event.
- `curb_crossing / continuation`
  - Current best pattern: middle-right crossing continuation to avoid centered reset.
  - Reason: rerun confirms it keeps the crossing alive without collapsing back into a generic frontal walk.
- `curb_crossing / handoff`
  - Current best pattern: right-edge blocking with the open road held to the opposite side.
  - Reason: latest micro-study and sequence rerun show this is more stable than `traffic opening` wording and remains visually distinct from entry and payoff.
- `curb_crossing / payoff`
  - Current best pattern: walks away from the wet crosswalk into the wider street.
  - Reason: latest blocking rerun confirms direct walk-away language is more stable than abstract `recedes into` or `far curb` phrasing and produces a real release/payoff event.
- `window_contact`
  - Current best pattern: same heroine + station/window edge + direct metal-frame contact + forward continuation.
  - Reason: latest probe shows actual tactile contact events without collapsing into reflection mood.
- `brace_pause`
  - Current best pattern: same heroine + wet rail + one braced hand + forward line still implied.
  - Reason: latest probe shows a readable brief pause that does not fully collapse into a static fashion pose.
- `sidewalk_continuation`
  - Current best pattern: `same heroine + wet sidewalk edge + next sidewalk-side stride + road clearly to her right`
  - Reason: the latest sequence rerun (`verse1_b1/b2/b3`) now keeps the heroine on a literal sidewalk edge, preserves the road on one side, and avoids collapsing back into a road-center walk.
- `blocking-sensitive release staging`
  - Current best pattern: `far-left edge entry -> middle-right carry -> right-edge handoff -> walk-away payoff`
  - Reason: latest blocking sequence rerun shows these four states are now visually distinct enough to behave as separate MV keyframes instead of centered repeats.

### Partially Closed
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
  - `same heroine + steps in from the far left edge of the wet crosswalk + most of the road stays open ahead`

### Final Chorus Continuation
- Best shape:
  - `same heroine + middle-right side of the wet crosswalk + same stride alive`

### Final Chorus Handoff
- Best shape:
  - `same heroine + right edge of the wet crosswalk + same stride carries forward + open road held to the left`

### Final Chorus Payoff
- Best shape:
  - `same heroine + walks away from the wet crosswalk into the wider street`

## What Counts As Failure
- Background changes to a different world family.
- The heroine recenters into a generic frontal walking image when blocking should differ.
- Event difference exists only in text but not in the image.
- Secondary trace/detail invents duplicate subjects or scene clutter.
- A later variant looks “safe” but visually collapses into the same keyframe role as the previous shot.

## Next Closure Order
1. Re-open `passage_compression` only if the current profile still needs a stronger non-platform compression event.
2. Treat blocking as `usable and sequence-validated`, but re-open it only if a later profile collapses back into centered entry or non-release payoff.
3. Move the next iteration focus to audio prompting and audio-visual sync behavior.

## Rule
Do not move on to denser story scripting until the current profile's active route/release families are fully closed and stable in real image sequence tests. This condition is currently satisfied for the example profile's active REF families.
