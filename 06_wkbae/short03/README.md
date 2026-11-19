# MD2Short

마크다운 문서 1개를 입력하면 한국어 9:16 숏폼 영상(MP4)을 자동 생성하는 로컬 CLI.

- 제품 요구사항: [`docs/PRD.md`](docs/PRD.md)
- 시스템 설계: [`docs/architecture.md`](docs/architecture.md)
- 작업 원칙: [`AGENTS.md`](AGENTS.md)

## 1. 사전 준비

| 도구 | 용도 | 설치 (macOS) |
| --- | --- | --- |
| Python 3.12+ / [uv](https://docs.astral.sh/uv/) | CLI 실행 | `brew install uv` |
| Node.js 20+ / npm | Remotion 렌더 | `brew install node` |
| ffmpeg / ffprobe | 오디오 길이 측정·QC (자막 합성에는 사용하지 않음) | `brew install ffmpeg` |

## 2. 설치

```bash
uv sync                       # Python 의존성
(cd remotion && npm install)  # Remotion 의존성
```

## 3. API 키 (`.env`)

프로젝트 루트에 `.env`를 만든다. **절대 커밋하지 않는다.**

```dotenv
ELEVENLABS_API_KEY=...   # 필수 — TTS + Scribe
OPENAI_API_KEY=...       # 권장 — 대본 생성, photo 모드 필수
```

`ELEVENLABS_API_KEY`가 없으면 즉시 종료 코드 1로 실패한다. `OPENAI_API_KEY`가 없으면 대본은 마크다운 추출(fallback extract)로 만든다.

> **ElevenLabs 무료 플랜 주의**: 기본 voice(`v1jVu1Ky28piIPEJqRrm`, `docs/voice.md`)는 Voice Library voice라 API 사용에 유료 플랜이 필요하다. 무료 플랜 키는 `HTTP 402 paid_plan_required`로 실패하므로 premade voice를 지정한다: `uv run md2short run sample.md --voice EXAVITQu4vr4xnSDxMaL`.

## 4. 실행

```bash
uv run md2short run sample.md
```

결과:

- `jobs/<job_id>/edit/final.mp4` — Remotion 합성 결과 (audit 사본)
- `output/ret.mp4` — 최종 결과물 사본 (`-o ""`로 비활성화)
- `jobs/<job_id>/qc_report.json`, `status.json`, `logs/`

주요 옵션 (전체 명세는 `docs/architecture.md` §6):

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--visual-mode` | `emoticon` | `emoticon`(호랑이 PNG, deterministic) 또는 `photo`(gpt-image-2, 실패 시 emoticon 자동 fallback) |
| `--voice`, `-v` | `v1jVu1Ky28piIPEJqRrm` | ElevenLabs voice id |
| `--speed` | `1.0` | TTS 속도 0.7~1.2 |
| `--chunk-size` | `14` | 자막 segment 최대 단어 수 안전 상한 (1~24) |
| `--bg` | `0xFFFFFF` | 가운데 메인 섹션 배경색 |
| `--model` | `gpt-5-mini` | 대본 생성 모델 |
| `--no-opening` / `--outro` | opening on / outro off | 날짜 오프닝, 마지막 구독 CTA |
| `--output`, `-o` | `output/ret.mp4` | 최종 사본 경로 |

스토리보드 입력은 `### 1컷` 헤딩 아래 `- 자막: ...`, `- 화면 연출: ...`, `- 이미지 프롬프트: ...` 형식으로 작성한다. `자막`만 내레이션에 사용된다.

### 상태 조회 / 정리

```bash
uv run md2short status <job_id>
uv run md2short clean --older-than 7d --dry-run
uv run md2short clean --older-than 24h
```

종료 코드: `0` 성공, `1` 입력 검증 실패·필수 env 누락, `2` 실행 중 예외 또는 QC 실패.

## 5. 테스트

```bash
uv run pytest -q             # 외부 API 는 모두 mock. Remotion smoke render 포함
uv run pytest -q -m "not render"   # 렌더 테스트 제외
```

## 6. 브랜드 asset 교체

현재 로고·폰트는 placeholder다. 파일만 교체하면 코드 수정 없이 반영된다.

- `img/header_logo.png` — 상단 헤더 로고 (220px 높이 영역)
- `company/<slug>.png` — 회사 로고 cue (`company/README.md` 참고)
- `font/` + `font/font.css` — `SeoulAlrim` / `SeoulNotice` family alias
- `emoticon/` — 호랑이 캐릭터 PNG 60종. **저장소에 포함되지 않으므로(약 88MB) 별도로 받아 `emoticon/`에 넣어야 한다.** 파일명(`09_가즈아_상승.png` 등)은 `md2short/emoticon_map.py`의 `EMOTICON_KEYWORDS`와 일치해야 하며, 없으면 렌더와 `tests/test_emoticon_map.py`가 실패한다.
