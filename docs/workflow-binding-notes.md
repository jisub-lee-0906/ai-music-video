# Workflow Binding Notes

이 문서는 `workflows/` JSON을 수정하지 않고, 코드에서 어떤 노드 입력만 바인딩할지 정리한 읽기 전용 참고 문서다.

원칙:

- `workflows/*.json`은 절대 수정하지 않는다.
- 코드는 workflow의 기존 node id / input key에만 맞춘다.
- prompt 설계는 workflow 내부 예시 문체를 최대한 따른다.
- graph 구조를 바꾸지 않고 binding만 바꾼다.

대상 workflow:

- [audio_ace_step_1_5_split_4b.json](/D:/workspace/ai-music-video/workflows/audio_ace_step_1_5_split_4b.json)
- [image_flux2_text_to_image.json](/D:/workspace/ai-music-video/workflows/image_flux2_text_to_image.json)
- [image_flux2.json](/D:/workspace/ai-music-video/workflows/image_flux2.json)
- [video_ltx2_3_i2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_i2v.json)
- [video_ltx2_3_ia2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_ia2v.json)
- [video_ltx2_3_flf2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_flf2v.json)

## 1. ACE-Step 1.5

파일:

- [audio_ace_step_1_5_split_4b.json](/D:/workspace/ai-music-video/workflows/audio_ace_step_1_5_split_4b.json)

핵심 텍스트 노드:

- node `94`
  class: `TextEncodeAceStepAudio1.5`

바인딩 입력:

- `tags`
- `lyrics`
- `seed`
- `bpm`
- `duration`
- `language`
- `keyscale`

길이 관련 노드:

- node `98`
  input `seconds`

출력 파일명 노드:

- node `107`
  input `filename_prefix`

프롬프트 예시 문체:

- `tags`는 장르 설명형이다.
- 한두 단어 키워드가 아니라 2~3문장짜리 사운드 설명으로 들어간다.
- `lyrics`는 section label이 포함된 블록 구조다.

예시 특징:

- `Rock: ...`처럼 장르명으로 시작
- 사운드, 악기, 에너지, 구조를 문장으로 설명
- 가사는 `[Verse]`, `[Chorus]` 구조를 유지

시티팝 적용 원칙:

- `tags`는 시티팝 사운드 설명형 문체 유지
- `lyrics`는 필요 시 짧은 구조 가사로 유지
- ACE workflow에는 별도 profile context를 넣지 않는다

## 2. Flux2 still workflows

파일:

- [image_flux2_text_to_image.json](/D:/workspace/ai-music-video/workflows/image_flux2_text_to_image.json)
- [image_flux2.json](/D:/workspace/ai-music-video/workflows/image_flux2.json)

핵심 prompt 노드:

- T2I workflow node `98:6`
  class: `CLIPTextEncode`
  input: `text`
  역할: positive prompt

- REF workflow node `68:6`
  class: `CLIPTextEncode`
  input: `text`
  역할: positive prompt

크기 노드:

- T2I workflow node `98:47`
  inputs: `width`, `height`

- REF workflow node `68:47`
  inputs: `width`, `height`

샘플링 노드:

- T2I workflow node `98:25`
  input: `noise_seed`

- REF workflow node `68:25`
  input: `noise_seed`

- T2I workflow node `98:48`
  inputs: `steps`, `width`, `height`

- REF workflow node `68:48`
  inputs: `steps`, `width`, `height`

- T2I workflow node `98:26`
  input: `guidance`

- REF workflow node `68:26`
  input: `guidance`

출력 파일명 노드:

- node `9`
  input: `filename_prefix`

프롬프트 예시 문체:

- 자연어 설명/지시형
- 한 문장 또는 짧은 문단으로 장면을 명확히 설명하고, 필요할 때만 짧은 보존 제약을 추가

예시:

```text
A young woman in a satin bomber jacket leans under late-night station light, with reflective glass and soft neon spill, as one clean cinematic keyframe in the same continuous scene.
```

문체 특징:

- 공식 FLUX 예시처럼 자연어 prompt string을 우선한다
- 문법 선택은 local validation으로 결정하되, 쉼표 나열형을 기본 정답으로 가정하지 않는다
- FLUX.2 reference workflow에서는 reference image를 유지하면서 바꾸고 싶은 차이만 명시하는 문장이 우선이다

시티팝 적용 원칙:

- 기본 still은 자연어 설명형으로 subject, place, light, mood, composition을 한 장면으로 묶는다
- rerender/refinement는 기존 still identity를 유지하고 바꾸고 싶은 차이만 더한다
- still workflow에는 negative prompt node가 없으므로 negative prompt 규칙을 still 문법 중심으로 문서화하지 않는다

## 3. LTX 2.3 i2v

파일:

- [video_ltx2_3_i2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_i2v.json)

이미지 입력 노드:

- node `269`
  class: `LoadImage`
  input: `image`

크기 노드:

- node `267:257`
  input: `value`
  역할: width

- node `267:258`
  input: `value`
  역할: height

프레임/길이 노드:

- node `267:260`
  input: `value`
  역할: frame rate

- node `267:225`
  input: `value`
  역할: total frame length

프롬프트 생성 시드 노드:

- node `267:266`
  class: `PrimitiveStringMultiline`
  input: `value`
  역할: prompt seed

- node `267:274`
  class: `TextGenerateLTX2Prompt`
  input: `prompt`
  역할: prompt seed를 LTX style prompt로 변환

positive prompt 노드:

- node `267:240`
  class: `CLIPTextEncode`
  input: `text`

negative prompt 노드:

- node `267:247`
  class: `CLIPTextEncode`
  input: `text`

출력 파일명 노드:

- node `75`
  input: `filename_prefix`

예시 prompt seed 문체:

- 장문 자연어 지시형
- 피사체, 배경, 움직임, 카메라 제약까지 문장으로 넣는다

예시 특징:

- 인물 설명
- 행동 제약
- 카메라 move 제약
- 금지 move까지 자연어로 포함

권장 바인딩 전략:

- 코드에서는 node `267:266.value`에 shot seed를 넣는다
- `TextGenerateLTX2Prompt`가 정제한 텍스트를 downstream positive로 쓰게 둔다
- 직접 positive prompt 노드를 덮어쓰는 방식보다 seed node를 먼저 쓰는 쪽이 workflow 의도에 더 맞다

시티팝 prompt 원칙:

- 3~6문장 정도의 장면 지시형
- 장소, 인물, 동작, 카메라, 분위기 순서
- “single smooth push-in”, “static side-tracking”, “night coastal road” 같은 제약형 문구 유지

## 4. LTX 2.3 ia2v

파일:

- [video_ltx2_3_ia2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_ia2v.json)

이미지 입력 노드:

- node `269`
  class: `LoadImage`
  input: `image`

오디오 입력 노드:

- node `276`
  class: `LoadAudio`
  input: `audio`

오디오 trim 노드:

- node `340:332`
  inputs: `start_index`, `duration`, `audio`

길이 관련 노드:

- node `340:331`
  input: `value`
  역할: duration

- node `340:323`
  input: `value`
  역할: frame rate

- node `340:329`
  expression: `a * b + 1`
  역할: frame count 계산

프롬프트 생성 시드 노드:

- node `340:319`
  class: `PrimitiveStringMultiline`
  input: `value`

- node `340:342`
  class: `TextGenerateLTX2Prompt`
  input: `prompt`

positive prompt 노드:

- node `340:306`
  class: `CLIPTextEncode`
  input: `text`

negative prompt 노드:

- node `340:314`
  class: `CLIPTextEncode`
  input: `text`

출력 파일명 노드:

- node `341`
  input: `filename_prefix`

예시 prompt seed 문체:

- 장문 자연어 지시형
- 특히 `character`, `action`, `camera`, `scene`를 나눠 적는다

예시 특징:

- 말하는/행동하는 캐릭터
- 음악 반응형 퍼포먼스
- 카메라 고정 또는 추적 제약

시티팝 적용 원칙:

- 코러스나 퍼포먼스 샷에만 사용
- audio segment를 shot 길이에 맞춰 trim
- seed 문체는 `scene`, `character`, `action`, `camera`를 명시적으로 적는 방식이 안정적

## 5. LTX 2.3 flf2v

파일:

- [video_ltx2_3_flf2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_flf2v.json)

첫 프레임 입력 노드:

- node `31`
  class: `LoadImage`
  input: `image`

마지막 프레임 입력 노드:

- node `39`
  class: `LoadImage`
  input: `image`

크기 노드:

- node `129:113`
  input: `value`
  역할: width

- node `129:98`
  input: `value`
  역할: height

길이/프레임 노드:

- node `129:102`
  input: `value`
  역할: duration

- node `129:114`
  input: `value`
  역할: frame rate

- node `129:130`
  expression: `a * b + 1`
  역할: frame count 계산

positive prompt 노드:

- node `129:128`
  class: `CLIPTextEncode`
  input: `text`

negative prompt 노드:

- node `129:112`
  class: `CLIPTextEncode`
  input: `text`

출력 파일명 노드:

- node `68`
  input: `filename_prefix`

예시 positive prompt 문체:

```text
The camera move from a high position to a low position, keeping the character in the frame centered.
Music: Synthwave cyberpunk music with calm ambient synths and driving 80s beats.
```

문체 특징:

- 매우 짧다
- 전환 방향과 카메라 move만 명확히 말한다
- 배경 설명을 길게 풀지 않는다

시티팝 적용 원칙:

- `from -> to` 구조를 짧게 유지
- 장소 전환 또는 감정 브리지에만 사용
- i2v/ia2v처럼 긴 서사 프롬프트를 쓰지 않는다

## 6. 공통 바인딩 원칙

### Prompt 전략

- ACE: 장르 설명형 + 구조화 lyrics
- Flux2 stills: 쉼표 나열형 시각 설명 + rerender 시 reference-image refinement
- LTX i2v: 장문 장면 지시형
- LTX ia2v: 장문 장면 지시형 + 퍼포먼스/오디오 반응
- LTX flf2v: 짧은 브리지 지시형

### Output prefix

모든 workflow는 `filename_prefix`를 갖고 있으므로 코드에서 shot id 기반으로 강제한다.

예:

- `audio/<run_id>/music`
- `stills/<run_id>/S003`
- `clips/<run_id>/S003_i2v`
- `clips/<run_id>/S005_ia2v`
- `clips/<run_id>/S008_flf2v`

### Size / fps / duration

- width/height/fps/length는 모두 별도 primitive 노드가 있어서 JSON 구조를 바꾸지 않고 값만 바인딩 가능하다
- duration과 frame count는 workflow expression에 맡기고, 코드에서 직접 계산을 최소화하는 편이 좋다

### 금지

- workflow node 추가/삭제
- sampler 교체
- prompt generator chain 변경
- LoRA / checkpoint 이름 수정

## 7. 구현 전에 추가로 고정할 것

코드 들어가기 전에 mapper 수준에서 딱 두 가지만 더 고정하면 된다.

- 각 workflow에서 실제 바인딩할 node id 상수
- mode별 prompt builder 함수 출력 형식

권장 상수 예:

- `ACE_TEXT_NODE = "94"`
- `QWEN_POSITIVE_NODE = "76:6"`
- `QWEN_NEGATIVE_NODE = "76:7"`
- `LTX_I2V_PROMPT_SEED_NODE = "267:266"`
- `LTX_IA2V_PROMPT_SEED_NODE = "340:319"`
- `LTX_FLF2V_POSITIVE_NODE = "129:128"`

이 문서를 기준으로 mapper를 구현하면, workflow JSON은 끝까지 건드리지 않아도 된다.
