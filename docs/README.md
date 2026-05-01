# Docs guide

이 디렉터리는 현재 ai-music-video의 문서 truth surface만 남기고, 날짜가 붙은 분석/계획 문서는 역할을 분리해 유지한다.

## Current source of truth

우선순위는 아래 순서다.

1. `/README.md`
   - 현재 제품 정체성
   - 공개 CLI 사용법
   - artifact contract
   - WSL 사용 가이드
2. `docs/shared-comfyui.md`
   - Krita/Blender/ai-music-video가 Windows ComfyUI 하나를 공유하는 운영 기준
   - 중복 backend(예: 8000 + 8001) 진단과 WSL wrapper guard 설명
3. `docs/quality-findings.md`
   - manual frame/MV review에서 사용할 known quality finding code 목록
   - `ai-mv quality-findings-template` scaffold와 동기화되어야 하는 reviewer-facing guide
4. `docs/sample-config.yaml`
   - 샘플 override 설정
   - canonical default 자체는 아니며 실제 default truth는 코드에 있다
5. `docs/plans/2026-04-23-ai-mv-completion-roadmap.md`
   - 현재 남은 병목과 우선 실행 순서
   - 현재 작업 재개 시 기준 계획서

## Supporting analysis

다음 문서는 현재 구조를 이해하기 위한 분석 증거다.

- `docs/analysis/2026-04-23-topdown-validation-report.md`
- `docs/analysis/2026-04-23-ai-mv-system-analysis.md`
- `docs/analysis/2026-04-23-ai-mv-system-flow.mmd`
- `docs/analysis/2026-04-23-ai-mv-system-flow.svg`

주의:
- 이 파일들은 날짜 기준 분석 스냅샷이다.
- 숫자/테스트 개수/관찰 결과는 작성 시점 기준일 수 있다.
- 현재 truth가 필요하면 먼저 루트 `README.md`와 live code/tests를 본다.

## Historical docs

다음 문서는 삭제하지 않고 historical로 분리 보관한다.

- `docs/archive/2026-04-23-mv-final-7-percent.md`

이 문서는 현재 roadmap보다 더 좁은 slice-focused 계획이라서, 현재 canonical execution plan으로 쓰지 않는다.

## Cleanup rules

- 새 canonical 계획이 생기면 이전 좁은 계획 문서는 `docs/archive/`로 이동한다.
- generated artifacts, review packet outputs, frame dumps, 실험 스크립트는 `docs/` 아래에 두지 않는다.
- dated analysis 문서를 수정해야 할 때는 원문을 덮어쓰기보다 새 dated 문서를 추가하거나, `README.md`/`docs/README.md`에서 현재 truth를 다시 선언한다.
