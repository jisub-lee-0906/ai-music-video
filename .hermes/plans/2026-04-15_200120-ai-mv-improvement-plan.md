# ai-mv 추가 개선 계획

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task.

Goal: 현재 `ai-mv`를 “돌아가는 MVP” 수준에서 “명확한 제품 계약 + 안정적인 실행 + 유지보수 가능한 구조” 수준으로 끌어올린다.

Architecture: 우선순위는 1) 깨진 테스트와 실행 환경 계약을 바로잡아 기반을 안정화하고, 2) 제품/CLI/문서 계약을 하나로 통일하고, 3) 비대해진 planner/stage 로직을 분해해 유지보수성을 높이고, 4) 실제 결과물 품질 검수를 강화하는 순서로 가져간다. 기능 추가보다 먼저 제품 방향과 코드 구조의 드리프트를 줄이는 것이 효과가 크다.

Tech Stack: Python 3.11+, pytest, local ComfyUI, ffmpeg/ffprobe, Codex CLI, WSL wrapper scripts

---

## 현재 진단 요약

관찰한 사실:
- 테스트는 `uv run pytest -q` 기준 172개 중 169개 통과, 3개 실패다.
- 실패는 모두 `src/ai_mv/infra/codex_cli_client.py`의 명령 탐색/검증 순서와 테스트 고립성 문제에 묶여 있다.
- 제품 방향 문서는 “시티팝 전용 + 최소 입력 `concept_text` 중심”으로 정리되어 있는데, README/CLI/config에는 아직 `profile`, `--brief`, `director_brief_example.yaml` 등 레거시 표현이 남아 있다.
- 핵심 파일이 과대하다: `src/ai_mv/engines/acestep_1_5_aio/planner.py` 1058 lines, `src/ai_mv/core/stages/plan_citypop_mv.py` 720 lines, `src/ai_mv/core/contracts/prompt_normalize.py` 643 lines.
- 리뷰 단계는 현재 파일 존재 여부와 길이 차이 위주라서 실제 결과물 품질 검수라고 보기엔 약하다.

근거 파일:
- `README.md`
- `docs/citypop-mv-master-plan.md`
- `src/ai_mv/core/orchestration/config_defaults.py`
- `src/ai_mv/infra/codex_cli_client.py`
- `src/ai_mv/core/stages/plan_citypop_mv.py`
- `src/ai_mv/core/stages/review_outputs.py`
- `src/ai_mv/core/stages/render_stills.py`

---

## 추천 우선순위

1. 안정성 회복: Codex CLI 테스트/실행 계약 정리
2. 제품 계약 통일: README, CLI, config, docs의 레거시 제거
3. 구조 개선: planner/stage 대형 파일 분해
4. 품질 향상: 결과물 기반 review 자동화 강화
5. 운영성 개선: WSL/ComfyUI 상태 가시성, 재현성, artifact 관리

---

## 작업 스트림 A — 테스트/실행 안정화

### 목적
Codex CLI 관련 실패 3건을 먼저 제거해서 “기본 테스트가 항상 통과하는 저장소” 상태를 만든다.

### 문제 정의
현재 `generate_structured()`와 `assert_codex_ready()`가 테스트에서 `_run`, `_load_output`, `_login_status`를 monkeypatch하더라도 그 전에 `_codex_command_parts()`가 실제 실행환경을 조회해 실패할 수 있다. 즉, 테스트가 외부 환경에 과도하게 결합돼 있다.

### 변경 후보 파일
- Modify: `src/ai_mv/infra/codex_cli_client.py`
- Modify: `tests/unit/test_codex_cli_client.py`
- Optional: `src/ai_mv/infra/doctor_checks.py`

### 실행 단계
1. `codex_cli_client.py`에서 “명령 탐색”과 “로그인/실행/스키마 검증” 책임을 분리한다.
2. `_codex_command_parts()`를 직접 호출하지 않는 순수 helper 또는 injectable resolver를 만든다.
3. 테스트가 실제 `codex` 바이너리 존재 여부와 무관하게 동작하도록 monkeypatch 대상 경계를 재설계한다.
4. “실행파일 없음”, “로그인 안 됨”, “schema validation failed”를 서로 분리된 오류 시나리오로 테스트한다.
5. `uv run pytest tests/unit/test_codex_cli_client.py -q` 통과를 확인한다.
6. `uv run pytest -q` 전체 재검증을 수행한다.

### 완료 기준
- 현재 실패 3개가 모두 해결된다.
- 테스트가 로컬/WSL/CI 어디서든 외부 codex 설치 여부와 무관하게 재현 가능하다.

### 검증 명령
- `uv run pytest tests/unit/test_codex_cli_client.py -q`
- `uv run pytest -q`

---

## 작업 스트림 B — 제품 계약 정리(레거시 제거)

### 목적
프로젝트의 실제 방향인 “시티팝 전용 CLI 파이프라인”과 사용자 접점(README/CLI/config/docs)을 일치시킨다.

### 문제 정의
문서와 코드가 섞여 있다.
- `README.md`는 아직 `profiles/director_brief_example.yaml`과 `--brief` 흐름을 노출한다.
- `docs/citypop-mv-master-plan.md`는 profile 제거, `concept_text` 중심 입력을 선언한다.
- `src/ai_mv/cli/args.py`, `src/ai_mv/cli/commands.py`, `entrypoints/*.py`에는 `legacy_brief`, `audio_brief`, `audio_hook_brief` 경로가 살아 있다.
- `config_defaults.py` 기본 길이는 150~180초인데 문서 MVP는 15~30초에 가깝다.

### 변경 후보 파일
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/citypop-mv-master-plan.md` (필요 시 최신 구현 기준 보강)
- Modify: `src/ai_mv/cli/args.py`
- Modify: `src/ai_mv/cli/commands.py`
- Modify: `src/ai_mv/entrypoints/start.py`
- Modify: `src/ai_mv/entrypoints/preflight.py`
- Modify: `src/ai_mv/core/orchestration/config_defaults.py`
- Optional remove/deprecate: `profiles/director_brief_example.yaml`

### 실행 단계
1. 사용자에게 노출할 canonical 입력 계약을 하나로 확정한다.
   - 최소안: `concept_text` + optional duration/seed
   - 유지 필요 시: `audio_brief`, `audio_hook_brief`는 내부 고급 옵션으로만 숨김
2. CLI에서 `--brief`를 deprecated 경고로 전환하거나 제거한다.
3. README의 설치/실행 예시를 현재 WSL wrapper 및 `concept_text` 중심으로 전면 교체한다.
4. config 기본 duration 정책을 문서와 실제 목표에 맞게 조정한다.
5. profile 기반 문서/샘플이 정말 필요 없는지 결정하고, 불필요하면 제거한다.
6. 관련 unit test를 추가/수정해 CLI 인자 계약을 고정한다.

### 완료 기준
- 신규 사용자가 README만 읽고 현재 의도된 경로로 첫 실행 가능하다.
- 제품 방향과 CLI 계약이 문서/코드 모두에서 일관된다.
- “레거시 brief/profile 흐름”이 사용자 경험을 혼란시키지 않는다.

### 검증 명령
- `uv run pytest tests/unit/test_cli_args.py -q`
- `uv run pytest tests/unit/test_preflight_entrypoint.py -q`
- `uv run pytest tests/unit/test_start_entrypoint.py -q`
- `uv run pytest -q`

---

## 작업 스트림 C — planner/stage 로직 모듈화

### 목적
비대해진 핵심 파일을 분해해서 다음 개선(품질/기능)을 안전하게 얹을 수 있게 만든다.

### 문제 정의
현재 가장 중요한 도메인 로직이 거대한 단일 파일에 몰려 있다.
- `src/ai_mv/engines/acestep_1_5_aio/planner.py`
- `src/ai_mv/core/stages/plan_citypop_mv.py`
- `src/ai_mv/core/contracts/prompt_normalize.py`
이 상태에서는 작은 수정도 회귀 위험이 크고 테스트 범위 파악이 어렵다.

### 변경 후보 파일/신규 모듈 예시
- Create: `src/ai_mv/core/planning/section_normalizer.py`
- Create: `src/ai_mv/core/planning/shot_builder.py`
- Create: `src/ai_mv/core/planning/render_routing.py`
- Create: `src/ai_mv/core/planning/prompt_seed_builder.py`
- Create: `src/ai_mv/core/planning/citypop_bible.py`
- Modify: `src/ai_mv/core/stages/plan_citypop_mv.py`
- Create: `src/ai_mv/engines/acestep_1_5_aio/songform.py`
- Create: `src/ai_mv/engines/acestep_1_5_aio/lyrics_planning.py`
- Create: `src/ai_mv/engines/acestep_1_5_aio/audio_prompt_contract.py`
- Modify: `src/ai_mv/engines/acestep_1_5_aio/planner.py`

### 실행 단계
1. `plan_citypop_mv.py`에서 아래 책임을 분리한다.
   - 섹션 정규화
   - 샷 분할
   - ia2v/flf2v 라우팅
   - prompt seed/draft/polish 입력 구성
   - citypop bible 상수
2. `acestep_1_5_aio/planner.py`를 “입력 정규화 / 송폼 계획 / 가사 계획 / 후처리” 단위로 자른다.
3. dataclass 또는 TypedDict로 `section`, `shot`, `render_item` 계약을 명시한다.
4. 각 helper별 unit test를 잘게 추가한다.
5. 기존 public stage 함수 시그니처는 최대한 유지해 회귀 범위를 줄인다.

### 완료 기준
- 대형 파일이 도메인별 모듈로 분리된다.
- 순수 함수 테스트 비율이 높아져 수정 속도가 빨라진다.
- shot planning 규칙 변경이 테스트로 보호된다.

### 검증 명령
- `uv run pytest tests/unit/test_citypop_plan.py -q`
- `uv run pytest tests/unit/test_citypop_stages.py -q`
- `uv run pytest tests/unit/test_audio_planner_prompt.py -q`
- `uv run pytest -q`

---

## 작업 스트림 D — 리뷰 품질 게이트 강화

### 목적
현재의 “파일이 존재하면 일단 통과”에 가까운 review를 실제 결과물 품질 중심으로 끌어올린다.

### 문제 정의
`src/ai_mv/core/stages/review_outputs.py`는 아직 다음 수준에 머물러 있다.
- still/clip/final_video 파일 존재 여부
- audio/video duration drift
- 일부 placeholder 성격의 blocking/non-blocking checks
실제 제품 목표인 citypop fit, identity consistency, motion quality를 제대로 자동 점검하지 못한다.

### 변경 후보 파일
- Modify: `src/ai_mv/core/stages/review_outputs.py`
- Modify: `src/ai_mv/core/stages/render_stills.py`
- Modify: `src/ai_mv/core/stages/render_clips.py`
- Modify: `src/ai_mv/core/artifacts/run_summary.py`
- Create: `src/ai_mv/core/review/review_models.py`
- Create: `src/ai_mv/core/review/review_rules.py`
- Create: `src/ai_mv/core/review/coverage_metrics.py`
- Optional: `tests/unit/test_quality_review.py`

### 실행 단계
1. review 입력 계약을 확장한다.
   - shot별 프롬프트/seed/render_mode
   - still/clip 산출 경로
   - 섹션 커버리지와 계획 대비 실제 결과 연결
2. 최소한의 정량 규칙을 추가한다.
   - 계획 샷 수 대비 산출물 커버리지
   - render_mode별 성공률
   - 최종 영상 길이 편차 허용 범위
   - rerender 우선순위 산정
3. 가능하면 이미지/비디오 메타 기반의 추가 검사도 넣는다.
   - 해상도 일치
   - fps 일치
   - zero-byte/깨진 파일 방지
4. review_report를 더 풍부하게 만들어 “왜 재렌더가 필요한지”를 설명하게 한다.
5. 최종적으로 review 결과를 바탕으로 자동 재시도 전략까지 연결할 수 있게 모델을 준비한다.

### 완료 기준
- review_report가 pass/fail 사유를 설명한다.
- 사용자가 rerender 대상을 shot 단위로 바로 확인할 수 있다.
- 품질 저하가 단순 파일 존재 체크를 통과하지 못한다.

### 검증 명령
- `uv run pytest tests/unit/test_status.py -q`
- `uv run pytest tests/unit/test_pipeline.py -q`
- `uv run pytest tests/integration/test_pipeline_smoke.py -q`

---

## 작업 스트림 E — 운영성/재현성 개선

### 목적
WSL + Windows ComfyUI 환경에서 첫 성공 확률과 디버깅 속도를 높인다.

### 문제 정의
이미 WSL wrapper는 마련돼 있지만, 사용자 입장에선 “무엇이 왜 실패했는지”를 더 잘 보여주는 운영 도구가 필요하다.

### 변경 후보 파일
- Modify: `scripts/doctor-wsl.sh`
- Modify: `scripts/preflight-wsl.sh`
- Modify: `scripts/start-wsl.sh`
- Modify: `scripts/lib/wsl-env.sh`
- Modify: `src/ai_mv/infra/doctor_checks.py`
- Modify: `src/ai_mv/core/artifacts/manifest.py`
- Modify: `src/ai_mv/core/state/state_store.py`

### 실행 단계
1. doctor 출력에 더 많은 핵심 진단을 추가한다.
   - ComfyUI reachable 여부
   - workflow 파일 존재/해시
   - ffmpeg/ffprobe/codex 존재 여부
   - 입력/출력 디렉터리 접근 가능 여부
2. start/preflight wrapper가 최종 유효 config snapshot을 항상 남기게 한다.
3. run artifact에 “실패 원인 요약”과 “환경 스냅샷”을 남긴다.
4. 장기적으로는 stage별 소요시간/성공률 통계를 저장해 병목을 추적한다.

### 완료 기준
- 실패 시 원인 파악 시간이 짧아진다.
- 동일 설정으로 재실행하기 쉬워진다.
- WSL에서의 첫 샘플 런 성공률이 올라간다.

### 검증 명령
- `./scripts/doctor-wsl.sh`
- `./scripts/preflight-wsl.sh --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'`
- 필요 시 `./scripts/start-wsl.sh --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'`

---

## 추천 실행 순서(현실적인 2주 플랜)

### Phase 1: 기반 안정화 (반나절~1일)
- 스트림 A 완료
- 전체 pytest green 만들기

### Phase 2: 사용자 계약 정리 (1일)
- 스트림 B 완료
- README/CLI/config 드리프트 제거

### Phase 3: 구조 리팩터링 (2~4일)
- 스트림 C를 작은 PR/커밋 단위로 분할 수행

### Phase 4: 품질 게이트 강화 (1~2일)
- 스트림 D 완료
- review_report 개선

### Phase 5: 운영성 향상 (1일)
- 스트림 E 완료
- WSL 진단/재현성 개선

---

## 가장 먼저 착수하면 좋은 3가지

1. `src/ai_mv/infra/codex_cli_client.py` 테스트 실패 3건 해결
2. `README.md`와 `src/ai_mv/cli/args.py`에서 레거시 입력 계약 정리
3. `src/ai_mv/core/stages/plan_citypop_mv.py`를 4~5개 모듈로 분해 시작

이 3가지만 해도 체감 효과가 가장 크다:
- 저장소 신뢰도 상승
- 신규 실행 진입장벽 감소
- 이후 개선 작업 속도 증가

---

## 리스크와 트레이드오프

- 레거시 CLI 옵션을 빨리 제거하면 기존 사용 흐름이 깨질 수 있다.
  - 대응: 1~2 릴리즈 동안 deprecated 경고를 두고 제거
- planner 분해는 회귀 위험이 있다.
  - 대응: 먼저 golden-style unit tests를 늘린 후 분해
- review 고도화는 실제 샘플 데이터를 더 요구할 수 있다.
  - 대응: 1차는 메타데이터/coverage 규칙부터 시작

---

## 오픈 질문

- 이 프로젝트를 정말 `concept_text` 중심 단일 입력 UX로 밀고 갈지, 아니면 `audio_brief`/`hook_brief`를 고급 옵션으로 유지할지?
- profile 관련 산출물/문서를 완전히 제거할지, 아니면 호환 계층으로 남길지?
- review 단계에 LLM/vision 기반 평가를 넣을지, 아니면 우선 규칙 기반 평가만 강화할지?

---

## 최종 제안

추가 개선의 출발점은 “새 기능 추가”가 아니라 “드리프트 정리”가 가장 좋다. 특히 지금은 제품 정의가 이미 문서로는 명확한데, 코드/문서/CLI가 그 정의를 완전히 따라가지 못하고 있다. 따라서 다음 순서가 최적이다:

1. 테스트 green 복구
2. 제품 계약 통일
3. planner 구조 분해
4. review 품질 강화
5. WSL 운영성 개선

이 순서대로 가면 이후에는 더 공격적으로 shot planning, visual consistency, auto-rerender 같은 기능 개선을 얹기 쉬워진다.
