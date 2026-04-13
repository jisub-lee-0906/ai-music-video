# First Run Checklist

이 문서는 모델 다운로드가 끝난 뒤 첫 실제 샘플 런 전에 확인할 체크리스트다.

## 1. Workflow

- `workflows/` 아래 5개 파일만 존재하는지 확인
- workflow JSON을 수정하지 않았는지 확인
- ComfyUI에서 각 workflow가 수동 로드 가능한지 확인

## 2. Models

- ACE-Step 1.5 관련 모델 다운로드 완료
- Qwen-Image 관련 모델 다운로드 완료
- LTX 2.3 `i2v / ia2v / flf2v` 관련 모델 다운로드 완료
- workflow가 참조하는 VAE/CLIP/audio node 모델명과 실제 파일명이 일치하는지 확인

## 3. Paths

- `integrations.comfyui_input_dir` 존재
- `integrations.comfyui_output_dir` 존재
- `integrations.workflows_dir`가 현재 repo의 `workflows`를 가리키는지 확인
- `ffmpeg`, `ffprobe`가 PATH에 있는지 확인

## 4. First Sample

권장 첫 샘플:

- `concept_text`: `Japanese 80s city pop night drive, neon coast, bittersweet summer romance`
- planning:
  - `enable_ia2v=false`
  - `enable_flf2v=false`
- 오디오 길이: `15~20초`

## 5. Run Order

1. `preflight` 실행
2. `start` 실행
3. 산출물 확인:
   - `manifest.json`
   - `run_summary.json`
   - `stills/*.png`
   - `clips/*.mp4`
   - `final/final_mv.mp4`
   - `review_report.json`

## 6. Pass Criteria

- 모든 still 생성
- 모든 clip 생성
- `final_mv.mp4` 생성
- `review_report.status=done`
- `rerender_targets=[]`

## 7. First Retry Rules

- still 실패면 Qwen prompt/seed만 먼저 확인
- clip 실패면 해당 mode의 workflow binding부터 확인
- ffmpeg 실패면 clip 경로와 audio 경로부터 확인
- 첫 런에서는 `ia2v`, `flf2v`를 끄고 M1 경로부터 통과시킬 것
