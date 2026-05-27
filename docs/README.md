# Docs guide

이 디렉터리는 풀런 직전 혼동을 줄이기 위해 현재 확실한 문서만 남긴다.

## Current source of truth

우선순위는 아래 순서다.

1. `/README.md`
   - 현재 제품 정체성
   - 사용자-facing CLI 사용법
   - Flux TTI identity anchor → Flux reference pose/action anchors → IA2V-only generation canon
   - artifact contract
   - 레거시 Linux-bridge 운영 주의점
2. `docs/full-run-default-inputs.md`
   - 현재 풀런 테스트에 사용할 기본 `concept_text`
   - 추천 `run_id`
   - preflight/full-run/validate-latest 명령
   - 풀런에서 기대하는 anchor/reference routing 검증 기준

## Cleanup rules

- 현재 truth는 루트 `README.md`, `docs/full-run-default-inputs.md`, live code/tests를 우선한다.
- 날짜가 붙은 분석 문서, 과거 roadmap, 실험 로그, generated artifacts, review packet outputs, frame dumps, 임시 config 예시는 active `docs/` surface에 두지 않는다.
- `artifacts/`는 실행 산출물 위치이며 git ignored이다. 새 풀런 판단을 흐리지 않도록 풀런 전에는 비워도 된다.
- 새 canonical 방향이 생기면 과거 계획을 누적하지 말고 `/README.md`와 이 파일, 필요 시 `docs/full-run-default-inputs.md`만 갱신한다.
