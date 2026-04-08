# M3 FLF2V Spec

이 문서는 `LTX flf2v`를 도입하는 M3 브리지 명세다.

범위:

- 계획된 bridge shot에 `flf2v` 적용

비범위:

- 모든 인접 샷 자동 연결
- WAN식 전체 pair chaining

## 1. FLF2V를 쓰는 조건

`flf2v`는 아래일 때만 사용:

- 장소 전환
- 시간대 전환
- 감정 릴리즈 전환
- section bridge

금지:

- 모든 shot 사이 기계적 연결
- 단순 static mood shot
- chorus 퍼포먼스 shot

## 2. Input Selection

필수 입력:

- `first_still`
- `last_still`
- `duration_sec`
- `fps`

선정 규칙:

- 시작 샷 still과 종료 샷 still이 모두 존재해야 한다
- 시각 차이가 너무 작으면 `i2v`로 대체
- 브리지 길이는 `3`에서 `6`초 권장

## 3. Prompt Rule

`flf2v` prompt 형식:

- 매우 짧은 브리지 지시형
- `from -> to` 또는 카메라 move 중심

필수 요소:

- 카메라 방향 또는 전환 방향
- 주체 일관성 유지

금지:

- 긴 서사 프롬프트
- 장면 전체를 새로 설명하는 장문

## 4. Bridge Planning Rule

`flf2v` shot은 plan 단계에서 명시적으로 생성한다.

필수 필드:

- `bridge_from_shot_id`
- `bridge_to_shot_id`
- `render_mode=flf2v`

plan 기준:

- 전환이 실제로 필요할 때만 생성
- 곡당 bridge shot 수는 적게 유지

## 5. Review Rule

검수 항목:

- transition readability
- visual continuity
- camera motion stability
- no abrupt mismatch

rerender target 조건:

- 시작/종료 still 연결감 부족
- 전환이 부자연스러움
- 브리지 목적이 보이지 않음

## 6. Required Tests

- `test_m3_flf2v_gate.py`
- `test_bridge_selection_rule.py`
- `test_flf2v_input_binding.py`

## 7. Exit Criteria

- bridge shot 최소 1개 생성
- first/last still이 올바르게 바인딩
- 시각 전환 목적이 명확함
