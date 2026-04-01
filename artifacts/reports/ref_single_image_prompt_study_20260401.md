# REF Single-Image Prompt Study (2026-04-01)

## Goal
- Study one REF image at a time.
- Match prompt and image as closely as possible.
- Use the result as a concrete prompt-shape reference for future REF prompt engineering.

## Fixed Setup
- Anchor image:
  - [character_master_00042_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00042_.png)
- Test subject:
  - same heroine from the current TTI anchor
- Test case:
  - `bridge_b1`-type REF end frame
- Why this shot:
  - It previously failed through environment dominance and identity drift.
  - If this shot can be stabilized, the result is useful beyond easy walking shots.

## Iteration 1
- Prompt:
  - `The same Korean female idol slides her hand along the edge in a narrow station-side passage at night and leans a little closer to the glass.`
- Output:
  - [refstudy_bridge_b1_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_bridge_b1_v01_end_00001_.png)
- Result:
  - Strong identity continuity
  - Good side-body lean
  - Good hand-to-surface contact
  - The environment stays secondary
- Mismatch:
  - `glass` is present, but the specific sense of `sliding along the edge` is a little softer than the wording suggests
- Assessment:
  - Very strong

## Iteration 2
- Prompt:
  - `The same Korean female idol leans toward the station window in a narrow station-side passage at night, one hand sliding along the metal edge.`
- Output:
  - [refstudy_bridge_b1_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_bridge_b1_v02_end_00001_.png)
- Result:
  - Action reads clearly
  - `station window` and `metal edge` resolve well
  - Corridor depth is stronger and more literal
- Mismatch:
  - The smile becomes too strong and changes the tone
  - The frame becomes slightly more posed
- Assessment:
  - Good action fidelity, weaker mood fidelity

## Iteration 3
- Prompt:
  - `The same Korean female idol leans closer to the station window, one hand sliding along the metal edge in a narrow station-side passage at night.`
- Output:
  - [refstudy_bridge_b1_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_bridge_b1_v03_end_00001_.png)
- Result:
  - Best pure action match
  - `leans closer` resolves very directly
  - Window interaction is the subject of the frame
- Mismatch:
  - Hair continuity drifts away from the anchor
  - The ponytail is lost
- Assessment:
  - Best action wording, but identity continuity weakens

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail leans toward the station window in a narrow station-side passage at night, one hand sliding along the metal edge.`
- Output:
  - [refstudy_bridge_b1_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_bridge_b1_v04_end_00001_.png)
- Result:
  - Strong identity continuity
  - Ponytail preserved
  - Window interaction reads clearly
  - Hand-to-edge contact is clear
  - Environment supports the action instead of swallowing it
- Mismatch:
  - The output uses both hands visibly on the edge instead of one clearly isolated sliding hand
  - Minor, acceptable deviation
- Assessment:
  - Best overall balance of identity, action readability, and environment control

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail leans toward the station window in a narrow station-side passage at night, one hand sliding along the metal edge.`
- Best output:
  - [refstudy_bridge_b1_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_bridge_b1_v04_end_00001_.png)

## What This Taught Us

### 1. Compact subject-action-place order works
- The most reliable structure was:
  - `same heroine + identity hook + direct body action + single place anchor`
- This worked better than:
  - symbolic environment language
  - atmosphere-first phrasing
  - abstract compression wording

### 2. Literal environment nouns work better than poetic atmosphere
- `station window`
- `metal edge`
- `narrow station-side passage`
- These resolved better than:
  - `tight station pocket`
  - `quiet light`
  - `map-like glow`
  - `end of the night`

### 3. Identity continuity sometimes needs one explicit hook even with REF input
- The anchor alone was not always enough.
- Adding one small identity hook:
  - `with a high ponytail`
- materially improved continuity without turning the prompt into a hardcoded checklist.

### 4. The frame improves when the action implies close body-surface contact
- `leans toward`
- `one hand sliding along`
- These phrases kept the heroine large and readable.
- They also reduced architecture-dominant compositions.

## Prompt Pattern To Prefer For REF
- Recommended pattern:
  - `The same Korean female idol [small identity hook] [clear body action] [single place anchor] [single contact detail].`
- Example:
  - `The same Korean female idol with a high ponytail leans toward the station window in a narrow station-side passage at night, one hand sliding along the metal edge.`

## Prompt Pattern To Avoid For REF
- Avoid:
  - atmosphere-first lines
  - multiple environment symbols in one sentence
  - abstract compression language
  - tiny gesture plus heavy location wording
- Examples to avoid:
  - `tight station pocket`
  - `quiet light`
  - `map-like glow`
  - `the end of the night`

## Next Application
- Use this structure to rewrite other difficult REF shots, especially:
  - bridge
  - pre-chorus threshold shots
  - final chorus doorway shots
- Priority rule:
  - keep one heroine large and readable
  - keep one main action
  - keep one place anchor
  - add one identity hook only when continuity begins to drift
