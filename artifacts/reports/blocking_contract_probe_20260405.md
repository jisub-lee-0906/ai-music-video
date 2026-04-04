# Blocking Contract Probe (2026-04-05)

## Purpose
- Verify whether the new `direction_plan` blocking contract produces real image differences, not just better text contracts.
- Focus on the last unresolved MV problem:
  - entry shots collapsing to centered walking
  - payoff shots failing to read as walk-away release

## Tested Axes
- `edge_entry`
- `road-side re-entry`
- `middle-right carry`
- `right-edge handoff`
- `walk_away payoff`

## Best Results

### Edge Entry
- Best image:
  - ![edge01](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockfollow_edge01_00001_.png)
- Best prompt:
  - `The same Korean female idol steps in from the far left edge of the wet crosswalk at night, leaving most of the road open ahead of her.`
- Why it won:
  - breaks center framing clearly
  - keeps crosswalk geometry literal
  - reads as a new crossing event, not another generic walk

### Road-side Re-entry
- Best image:
  - ![verse2_reentry](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockprobe_verse2_b1_00001_.png)
- Best prompt:
  - `The same Korean female idol commits one step farther from the road-side edge of the wet sidewalk edge outside the station at night and keeps the station block stretching behind her.`
- Why it won:
  - produces a changed-angle return instead of repeating Verse 1
  - keeps the route grounded on the sidewalk edge

### Middle-right Carry
- Best image:
  - ![carry](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockprobe_final_chorus_b2_00001_.png)
- Best prompt:
  - `The same Korean female idol crosses through the middle-right side of the wet crosswalk at night, keeping the same stride alive.`
- Why it won:
  - avoids center reset
  - stays inside the same crossing event

### Right-edge Handoff
- Best image:
  - ![handoff](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockprobe_final_chorus_b3_00001_.png)
- Best prompt:
  - `The same Korean female idol carries the same stride along the right edge of the wet crosswalk at night, the open road holding to her left.`
- Why it won:
  - clearly differs from both entry and payoff
  - preserves route-side relation well

### Walk-away Payoff
- Best image:
  - ![away01](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockfollow_away01_00001_.png)
- Best prompt:
  - `The same Korean female idol walks away from the wet crosswalk into the wider street at night, leaving the crossing behind her.`
- Strong alternate:
  - ![away02](/C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_blockfollow_away02_00001_.png)
  - `The same Korean female idol moves away from the wet crosswalk at night, the wider street opening around her as she recedes.`
- Why these won:
  - rear-view departure is visually explicit
  - payoff finally reads as release instead of another frontal stride

## Failed Patterns
- `recedes into the wider street`
  - Often collapses back to a centered frontal heroine.
- `toward the far curb`
  - Reads weaker than direct walk-away language.
- abstract `off-center` or `frame-left` wording
  - Less reliable than physical place wording like `far left edge` or `right edge`.

## Sequence Result
- Final validation sheet:
  - [blocking_sequence_sheet_20260405a.png](D:/workspace/ai-music-video/artifacts/reports/blocking_sequence_sheet_20260405a.png)
- Sequence verdict:
  - usable for MV progression
  - entry, re-entry, carry, handoff, and walk-away are now visibly more distinct than before
  - intro gate shot still trends more centered than ideal, but does not break the larger sequence

## Final Takeaway
- Blocking now works best when expressed as **physical place relation**, not camera metadata.
- Best project-specific blocking language:
  - `far left edge`
  - `road-side edge`
  - `middle-right side`
  - `right edge`
  - `walks away`
- Current state:
  - blocking contract is **usable and sequence-validated**
  - strong enough to move focus to audio prompting next
