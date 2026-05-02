# Docs guide

이 디렉터리는 현재 ai-music-video의 문서 truth surface만 남긴다. 날짜가 붙은 과거 분석/계획 문서는 현재 canon을 흐리므로 이 repo의 active docs surface에서 제거한다.

## Current source of truth

우선순위는 아래 순서다.

1. `/README.md`
   - 현재 제품 정체성
   - 사용자-facing CLI 사용법
   - Flux TTI identity anchor → Flux reference pose/action anchors → IA2V-only generation canon
   - artifact contract
   - WSL 사용 가이드
2. `docs/shared-comfyui.md`
   - Krita/Blender/ai-music-video가 Windows ComfyUI 하나를 공유하는 운영 기준
   - 중복 backend 진단과 WSL wrapper guard 설명
3. `docs/quality-findings.md`
   - manual frame/MV review에서 사용할 known quality finding code 목록
   - `ai-mv quality-findings-template` scaffold와 동기화되어야 하는 reviewer-facing guide
4. `docs/sample-config.yaml`
   - 짧은 local smoke/test override 예시
   - canonical default 자체는 아니며 실제 default truth는 코드에 있다

## Cleanup rules

- 현재 truth는 루트 `README.md`와 live code/tests를 우선한다.
- 날짜가 붙은 분석 문서, 과거 roadmap, 실험 로그, generated artifacts, review packet outputs, frame dumps, 임시 스크립트는 active `docs/` surface에 두지 않는다.
- 새 canonical 방향이 생기면 과거 계획을 누적하지 말고 `/README.md`와 이 파일을 갱신한다.
