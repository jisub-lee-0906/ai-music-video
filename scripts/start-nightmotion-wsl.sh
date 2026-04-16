#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

CONCEPT_TEXT="Japanese 80s city pop night drive, bittersweet summer romance, late-night movement, unresolved longing turning into quiet resolve, neon reflections, station light, sea wind"
AUDIO_BRIEF="Modern short-form Japanese city pop. Verse should feel tactile and cinematic through concrete detail like wet glass, passing signs, station platforms, convenience-store light, and moving air. Pre-Chorus should stay tighter than the Chorus and build anticipation with fewer, cleaner phrases. Chorus should hit instantly with a short title-grade opening line, then widen emotionally without getting wordy. Bridge should be brief and turning. Final Chorus should answer the song and feel earned. Avoid dense literary wording, abstract monologues, and chorus lines that read like full prose sentences."
AUDIO_HOOK_BRIEF="The chorus needs a short title-worthy Japanese hook in the first line. Make it compact, memorable, and tied to late-night motion, station light, neon reflection, or the moment longing becomes quiet resolve. Avoid generic slogan hooks and avoid long sentence-shaped chorus openings."

exec "$SCRIPT_DIR/start-wsl.sh" \
  --concept-text "$CONCEPT_TEXT" \
  --audio-brief "$AUDIO_BRIEF" \
  --audio-hook-brief "$AUDIO_HOOK_BRIEF" \
  "$@"
