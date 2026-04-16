# Hermes AI Team Launcher v1

Goal: Create a desktop launcher that opens a 2x2 Windows Terminal layout for four Hermes roles (Coordinator, Routing, Prompting, Review), with reusable WSL helper scripts and rollback support.

Architecture:
- Windows side: a .ps1 launcher plus a double-clickable .cmd wrapper on the Desktop.
- WSL side: a reusable helper script under ~/.hermes/tools/hermes-ai-team/ that starts/attaches tmux-backed Hermes sessions and injects role prompts automatically.
- Safety: keep v1 project-configurable via one PowerShell variable, do not edit repo code, and ship a removal script for rollback.

Planned files:
- WSL helper dir:
  - ~/.hermes/tools/hermes-ai-team/launch-role-pane.sh
  - ~/.hermes/tools/hermes-ai-team/prompts/coordinator.txt
  - ~/.hermes/tools/hermes-ai-team/prompts/routing.txt
  - ~/.hermes/tools/hermes-ai-team/prompts/prompting.txt
  - ~/.hermes/tools/hermes-ai-team/prompts/review.txt
- Windows Desktop launcher dir:
  - /mnt/c/Users/Desktop/Desktop/Hermes AI Team Launcher/Launch-Hermes-AI-Team.ps1
  - /mnt/c/Users/Desktop/Desktop/Hermes AI Team Launcher/README.txt
  - /mnt/c/Users/Desktop/Desktop/Hermes AI Team Launcher/Remove-Hermes-AI-Team.cmd
- Desktop entrypoint:
  - /mnt/c/Users/Desktop/Desktop/Launch Hermes AI Team.cmd

Validation:
- Shell syntax-check the WSL helper script.
- PowerShell dry-run the launcher command construction.
- Confirm files exist in the expected Desktop/WSL locations.

Rollback:
- Run the generated Remove-Hermes-AI-Team.cmd script to remove Desktop launcher artifacts and the WSL helper directory.
