"""Typer CLI: run / status / clean (architecture.md §6).

종료 코드: 0 성공, 1 입력 검증 실패·필수 env 누락, 2 run_job() 실행 중 예외.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Literal, NoReturn, cast

import typer

from md2short import env
from md2short.schema import DEFAULT_VOICES, JobConfig

app = typer.Typer(add_completion=False, no_args_is_help=True, help="MD2Short — 마크다운 → 9:16 한국어 숏폼 MP4")

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_RUNTIME = 2

_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)([smhd]?)$")
_UNIT_SECONDS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


def _fail_input(message: str) -> NoReturn:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(EXIT_INPUT)


def _normalize_bg(bg: str) -> str:
    """JobConfig 저장 형식(0xRRGGBB)으로 정규화. 검증은 render.normalize_bg_color 단일 규칙."""
    from md2short.render import normalize_bg_color

    try:
        return "0x" + normalize_bg_color(bg)[1:]
    except ValueError:
        _fail_input(f"--bg 는 0xRRGGBB 또는 #RRGGBB 형식이어야 합니다: {bg!r}")


def parse_older_than(value: str) -> float:
    """'24h', '7d', '90m', '30s', '3600' -> seconds."""
    m = _DURATION_RE.match(value.strip())
    if not m:
        raise ValueError(f"invalid duration: {value!r}")
    return float(m.group(1)) * _UNIT_SECONDS[m.group(2)]


@app.command()
def run(
    markdown_file: Path = typer.Argument(..., help="입력 마크다운 파일"),
    lang: str = typer.Option("ko", "--lang", "-l", help="한국어 락 (v1.1+)"),
    voice: str = typer.Option(DEFAULT_VOICES["ko"], "--voice", "-v", help="ElevenLabs voice id"),
    speed: float = typer.Option(1.0, "--speed", help="TTS 속도 0.7~1.2"),
    template: str = typer.Option("tech_explainer", "--template", "-t", help="Remotion composition 은 TechExplainer 1종"),
    chunk_size: int = typer.Option(14, "--chunk-size", help="자막 segment max words 안전 상한 (1~24)"),
    bg: str = typer.Option("0xFFFFFF", "--bg", help="메인 섹션 배경색"),
    jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root", help="job 산출물 루트"),
    engine: str = typer.Option("remotion", "--engine", help="remotion 만 허용"),
    visual_mode: str = typer.Option("emoticon", "--visual-mode", help="emoticon | photo"),
    model: str = typer.Option("gpt-5-mini", "--model", help="OpenAI Responses API 대본 생성 모델"),
    output: str = typer.Option("output/ret.mp4", "--output", "-o", help="final MP4 사본 경로. 빈 문자열이면 비활성화"),
    opening: bool = typer.Option(True, "--opening/--no-opening", help="날짜 오프닝 표시"),
    outro: bool = typer.Option(True, "--outro/--no-outro", help="마지막 구독 CTA + 면책 문구 overlay 표시"),
) -> None:
    """마크다운 1개로 숏폼 영상 1편을 생성한다."""
    env.load_env()

    if lang != "ko":
        _fail_input(f"--lang 은 v1 에서 'ko' 만 지원합니다 (got {lang!r}). en/ja 는 v2 범위입니다.")
    if not 1 <= chunk_size <= 24:
        _fail_input(f"--chunk-size 는 1~24 범위여야 합니다 (got {chunk_size}).")
    if engine != "remotion":
        _fail_input(f"--engine 은 'remotion' 만 지원합니다 (got {engine!r}). ffmpeg 렌더 엔진은 지원하지 않습니다.")
    if visual_mode not in ("emoticon", "photo"):
        _fail_input(f"--visual-mode 는 emoticon | photo 중 하나여야 합니다 (got {visual_mode!r}).")
    if not 0.7 <= speed <= 1.2:
        _fail_input(f"--speed 는 0.7~1.2 범위여야 합니다 (got {speed}).")
    if not markdown_file.is_file():
        _fail_input(f"마크다운 파일을 찾을 수 없습니다: {markdown_file}")
    try:
        env.require_elevenlabs_key()
    except env.MissingEnvError as exc:
        _fail_input(str(exc))
    if visual_mode == "photo" and not env.get_openai_key():
        _fail_input("--visual-mode photo 는 OPENAI_API_KEY 가 필요합니다.")

    config = JobConfig(
        voice_id=voice,
        voice_speed=speed,
        template_id=template,
        bg_color=_normalize_bg(bg),
        chunk_size=chunk_size,
        visual_mode=cast(Literal["emoticon", "photo"], visual_mode),  # 위에서 검증됨
        show_opening=opening,
        show_outro=outro,
    )

    from md2short import pipeline

    def on_stage(stage: str) -> None:
        typer.echo(f"[md2short] {stage}")

    try:
        result = pipeline.run_job(
            markdown_file,
            config,
            jobs_root=jobs_root,
            model=model,
            output_path=Path(output) if output else None,
            on_stage=on_stage,
        )
    except Exception as exc:  # noqa: BLE001 — 모든 실행 예외는 종료 코드 2
        typer.secho(f"error: job failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(EXIT_RUNTIME) from exc

    typer.echo(f"job_id: {result['job_id']}")
    typer.echo(f"status: {result['status']}")
    typer.echo(f"final:  {result['final_mp4']}")
    if result.get("output_copy"):
        typer.echo(f"output: {result['output_copy']}")
    typer.echo(f"qc:     {result['qc_report']}")
    if result["status"] != "qc_passed":
        raise typer.Exit(EXIT_RUNTIME)


@app.command()
def status(
    job_id: str = typer.Argument(..., help="조회할 job id"),
    jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root"),
) -> None:
    """status.json 과 qc_report.json 요약을 출력한다."""
    job_dir = jobs_root / job_id
    status_path = job_dir / "status.json"
    if not status_path.is_file():
        _fail_input(f"job 을 찾을 수 없습니다: {status_path}")
    doc = json.loads(status_path.read_text(encoding="utf-8"))
    for key in ("job_id", "status", "started_at", "updated_at", "markdown_input", "engine", "script_chars", "error"):
        if key in doc:
            typer.echo(f"{key}: {doc[key]}")
    if "config" in doc:
        typer.echo(f"visual_mode: {doc['config'].get('visual_mode')}")
    qc_path = job_dir / "qc_report.json"
    if qc_path.is_file():
        report = json.loads(qc_path.read_text(encoding="utf-8"))
        typer.echo(f"qc_passed: {report['passed']}")
        for check in report["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            typer.echo(f"  [{mark}] {check['name']}: diff {check['diff_ms']}ms (±{check['tolerance_ms']}ms)")
        cost = report.get("cost_estimate", {})
        typer.echo(f"cost_estimate_usd: {cost.get('total_usd')}")


@app.command()
def clean(
    older_than: str = typer.Option(..., "--older-than", help="예: 3600, 30m, 24h, 7d"),
    dry_run: bool = typer.Option(False, "--dry-run", help="삭제하지 않고 목록만 출력"),
    jobs_root: Path = typer.Option(Path("jobs"), "--jobs-root"),
) -> None:
    """오래된 job 디렉터리(및 Remotion staging)를 삭제한다."""
    try:
        threshold = parse_older_than(older_than)
    except ValueError as exc:
        _fail_input(str(exc))
    if not jobs_root.is_dir():
        typer.echo("no jobs")
        return

    from md2short.render import PROJECT_ROOT

    cutoff = time.time() - threshold
    staging_root = PROJECT_ROOT / "remotion" / "public" / "jobs"
    targets = sorted(p for p in jobs_root.iterdir() if p.is_dir() and p.stat().st_mtime < cutoff)
    for job_dir in targets:
        if dry_run:
            typer.echo(f"would remove {job_dir}")
            continue
        shutil.rmtree(job_dir)
        staging = staging_root / job_dir.name
        if staging.is_dir():
            shutil.rmtree(staging)
        typer.echo(f"removed {job_dir}")
    typer.echo(f"{len(targets)} job(s) {'matched' if dry_run else 'removed'}")
