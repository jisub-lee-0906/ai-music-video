# Citypop MV Master Plan

Archived note:
- This document reflects an older citypop-first product reset.
- It is no longer canonical repo-wide product truth.
- Keep it only as historical context or future style-pack reference for `styles/citypop`.
- The current canonical direction is the concept-text-first, multi-style charter under `.hermes/plans/2026-04-15_202152-product-direction-charter.md`.

## 1. 제품 재정의

이 프로젝트는 더 이상 범용 AI 뮤직비디오 생성기가 아니다.

새 목표는 하나다.

- 일본 80~90년대 시티팝 감성에 고정된 뮤직비디오를 안정적으로 생성하는 로컬 CLI 파이프라인

이 결정으로 인해 다음은 제거한다.

- 장르 범용성
- 프로필 기반 커스터마이징
- Flux/WAN 호환성
- 스타일 자동 추론
- 범용 visual concept 조합 시스템

## 2. 고정 철학

핵심 원칙:

- 음악이 1순위다.
- 시각은 시티팝 고정 world bible 위에서만 움직인다.
- 가사는 보조 신호다.
- 코드는 prompt를 예쁘게 다듬지 않는다.
- LLM이 draft/polish를 담당한다.
- 최종 평가는 `png`, `mp4`, `final_mv.mp4`를 보고 한다.

실패 원인으로 간주하는 것:

- 범용성 때문에 shot semantics가 흔들리는 것
- profile field가 많아서 입력 품질이 불안정해지는 것
- workflow에 맞추지 않고 코드가 중간에서 의미를 재구성하는 것
- prompt 품질만 보고 실제 결과물 검수를 약하게 하는 것

## 3. 고정 세계관

프로필 시스템 대신 `citypop_bible`을 내부 고정 설정으로 둔다.

상위 고정 규칙:

- 시대감: 일본 80~90년대 시티팝
- 공간: 해안도로, 네온 시내, 석양 해변, 심야 드라이브, 옥상, 실내 카페, 차 안
- 색: sunset amber, ocean blue, sodium-vapor night, neon cyan, warm magenta accents
- 소품: 카세트, 카 오디오, 컨버터블, 팜트리, 간판, 창문 반사, 필름 그레인
- 인물상: 지나치게 현대적 K-pop 비주얼 금지, 과한 사이버펑크 금지, 복잡한 다인군상 금지
- 카메라: 부드러운 드리프트, 측면 추적, 전진 이동, 정적인 mood hold

## 4. 입력과 출력

최소 입력:

- `concept_text`
- `duration_sec`
- 선택적 `seed`

v1 입력 스펙:

| 필드 | 필수 | 설명 | 비고 |
| --- | --- | --- | --- |
| `concept_text` | 예 | 곡 무드, 장면 감정, 짧은 가사 씨앗을 함께 담는 단일 텍스트 | 별도 profile 없이 이것만 받는다 |
| `duration_sec` | 예 | 생성 목표 길이 | MVP는 `15`에서 `30` 사이로 제한 |
| `seed` | 아니오 | 재현용 시드 | 없으면 자동 생성 |

입력 canonical naming:

- 외부 입력 표준 필드명은 항상 `concept_text`다.
- 내부 코드도 원문 기준 필드는 `concept_text`를 유지한다.
- `concept`는 새 코드에서 canonical field로 사용하지 않는다.
- `lyrics_seed`는 독립 입력 필드가 아니라 `concept_text`에서 파생되는 내부 생성값이다.
- `songform`은 사용자 입력이 아니라 `audio` 또는 `plan` 단계에서 결정되는 내부 계획값이다.

v1에서 받지 않는 것:

- 별도 `lyrics` 필드
- 별도 `profile` 파일
- 스타일 선택 옵션
- 장르 선택 옵션
- 카메라 preset 선택

의도적으로 없애는 입력:

- profile yaml
- anchor clothing fields
- 범용 장소 목록
- 범용 props 목록
- genre switch

핵심 출력:

- 생성 음악
- shot plan
- shot stills
- shot clips
- final mv
- review report

## 5. 새 stage 구성

새 파이프라인:

1. `audio`
2. `plan`
3. `stills`
4. `clips`
5. `assemble`
6. `review`

각 stage 책임:

### `audio`

- ACE-Step 1.5로 곡 생성
- 섹션, beat, bar timing 생성
- 후속 시각 계획의 리듬 기준점 제공

### `plan`

- 음악 구조를 기준으로 샷을 분할
- 시티팝 world bible에 맞는 shot role 부여
- 각 샷의 render mode 결정
- seed prompt 생성 후 LLM draft/polish로 넘길 컨텍스트 생성

### `stills`

- Qwen-Image로 대표 still과 shot still 생성
- 인물/분위기/배경 정합성 유지
- LTX의 입력 image source를 안정화

### `clips`

- LTX 2.3으로 각 샷 비디오 생성
- shot 특성에 따라 `i2v`, `ia2v`, `flf2v`를 라우팅

### `assemble`

- ffmpeg로 클립 연결
- 구간 hold
- speed/trim/mux
- 최종 영상 길이를 오디오와 맞춤

### `review`

- 결과물 기반 자동 검수
- 재생성 대상 샷 식별
- 최종 pass/fail와 next action 기록

## 6. 핵심 데이터 계약

### `music_plan`

- `concept_text`
- `duration_sec`
- `bpm_target`
- `songform`
- `lyrics_seed`

### `music_map`

- `audio_path`
- `duration_sec`
- `sections`
- `beat_times_sec`
- `bar_times_sec`

### `shot_plan`

- `shot_id`
- `section_name`
- `section_type`
- `start_sec`
- `end_sec`
- `duration_sec`
- `shot_role`
- `visual_mode`
- `energy`
- `render_mode`

### `render_plan`

- `shot_id`
- `prompt_seed`
- `prompt_draft`
- `prompt_polish`
- `still_a`
- `still_b`
- `audio_segment`

M1 단순화 규칙:

- `master still`은 M1 필수 산출물이 아니다.
- M1에서는 shot별 `shot still`만 있으면 통과 가능하다.
- `still_b`는 M1에서 비워둘 수 있다.
- `audio_segment`는 M1에서 optional이다.

### `clip_result`

- `shot_id`
- `render_mode`
- `video_path`
- `duration_sec`
- `source_stills`

### `review_report`

- `identity_consistency`
- `citypop_fit`
- `motion_quality`
- `section_coverage`
- `audio_sync`
- `rerender_targets`

## 7. LTX 라우팅 규칙

기본 원칙:

- 기본값은 `i2v`
- 음악 반응형 퍼포먼스 샷은 `ia2v`
- 두 비주얼 상태 간 브리지는 `flf2v`

초기 규칙:

- `intro`, `verse`, `outro`의 정적 무드샷: `i2v`
- 보컬 존재감이 큰 `chorus` 퍼포먼스 샷: `ia2v`
- 장소 전환, 낮/밤 전환, 감정 릴리즈 브리지: `flf2v`

## 8. 잠금된 MVP 범위

1차 목표는 전곡 완성이 아니다.

MVP:

- 15초에서 30초 사이의 샘플 곡
- 4개에서 8개 샷
- `Qwen still -> LTX clip -> ffmpeg assemble`
- 리뷰 리포트까지 자동 생성

MVP에서 제외:

- profile system
- 다장르 지원
- 복잡한 사용자 설정
- 레거시 workflow fallback

마일스톤 잠금:

### M1. First Runnable

- 길이: `15`초에서 `20`초
- 샷 수: `4`개에서 `6`개
- 허용 workflow: `ACE-Step`, `Qwen`, `LTX i2v`, `ffmpeg`
- 모든 샷 render mode: `i2v`
- 필수 still 전략: 샷마다 `Qwen shot still` 1장
- 비필수 항목: `master still`, `transition still`, `audio_segment`, `ia2v`, `flf2v`
- 목표: `final_mv.mp4`와 `review_report.json`이 생성될 것

### M2. Music-Reactive

- 길이: `20`초에서 `30`초
- 샷 수: `5`개에서 `8`개
- 추가 workflow: `LTX ia2v`
- 허용 규칙: `chorus` 샷만 `ia2v`
- 목표: 코러스 구간에서 오디오 반응형 샷이 최소 1개 생성될 것

### M3. Transition-Complete

- 길이: `30`초 이상 샘플 또는 전곡 일부
- 추가 workflow: `LTX flf2v`
- 허용 규칙: bridge shot에 한해 `flf2v`
- 목표: section 전환 브리지가 최소 1개 포함될 것

## 9. 구현 우선순위

1. 새 문서와 stage 계약 고정
2. workflow 상수와 pipeline stage 이름 교체
3. `audio -> plan -> stills -> clips -> assemble` skeleton 연결
4. Qwen still renderer 구현
5. LTX `i2v` 우선 구현
6. ffmpeg assemble 단순판 구현
7. 결과물 review 구현
8. 이후 `ia2v`, `flf2v` 추가

## 10. 완료 기준

최종적으로 아래 조건을 만족해야 한다.

- 프로필 없이 실행 가능하다.
- 시티팝 스타일이 기본값이 아니라 고정값이다.
- `Flux/WAN` 코드 경로가 실제 실행에서 완전히 제거된다.
- 1곡 샘플에서 `audio -> final_mv.mp4`가 끝까지 나온다.
- review report가 재생성 대상 샷을 지정할 수 있다.

릴리스 통과 기준:

- 샘플 실행 3회 중 3회가 중단 없이 완료된다.
- 최종 비디오 길이와 오디오 길이 차이가 `0.3`초 이하다.
- 전체 샷 중 실패 또는 수동 폐기 대상이 `20%` 이하다.
- 수동 검수 체크리스트에서 `citypop fit`이 `pass`다.
- 재생성 루프 없이도 최소 1회 usable output이 나온다.

수동 검수 체크리스트:

- Blocking:
  인물/스타일이 시티팝 world bible과 어긋나지 않는다.

- Blocking:
  샷 간 무드와 색감이 크게 튀지 않는다.

- Blocking:
  결과물이 K-pop, cyberpunk, generic anime montage로 보이지 않는다.

- Non-blocking:
  카메라 움직임이 과도하게 현대적이거나 공격적이지 않다.

- Non-blocking:
  최소 1개의 memorable shot이 존재한다.

수동 검수 pass rule:

- Blocking 3개는 모두 통과해야 한다.
- Non-blocking 2개 중 최소 1개는 통과해야 한다.
- Blocking 중 1개라도 실패하면 해당 run은 release candidate로 인정하지 않는다.
