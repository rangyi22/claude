"""단일 job 오케스트레이션 (architecture.md §2.1).

외부 모듈은 `module.function` 형태로 호출한다 — 테스트가 monkeypatch 로 교체할 수 있게.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from md2short import (
    caption_plan,
    data_extract,
    emoticon_map,
    env,
    numeric_display,
    opening,
    photo_engine,
    qc,
    render,
    script_engine,
    state,
    storyboard,
    transcript,
    voice,
)
from md2short.schema import CTA_TEXT, JobConfig

DEFAULT_OUTPUT_COPY = Path("output/ret.mp4")
JOB_SUBDIRS = ("inputs", "audio", "transcripts", "edit", "logs", "thumbs")

OnStage = Callable[[str], None]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _opening_word_count(words: list[dict], opening_ms: int) -> int:
    return sum(1 for w in words if int(w["end"]) <= opening_ms) if opening_ms > 0 else 0


def _storyboard_segments(sb: dict, words: list[dict], opening_ms: int) -> list[dict]:
    """컷을 words.json 문장 boundary 에 매핑. opening 단어는 제외하고 인덱스를 원래 words 기준으로 복원."""
    offset = _opening_word_count(words, opening_ms)
    segments = storyboard.map_cuts_to_segments(sb, words[offset:])
    for seg in segments:
        seg["wordStart"] += offset
        seg["wordEnd"] += offset
        if seg.get("imagePrompt"):
            seg["image_prompt"] = seg["imagePrompt"]
    return segments


def run_job(
    markdown_path: Path,
    config: JobConfig,
    *,
    jobs_root: Path = Path("jobs"),
    model: str = script_engine.DEFAULT_MODEL,
    output_path: Path | None = DEFAULT_OUTPUT_COPY,
    on_stage: OnStage | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """마크다운 1개 → job 1개. 결과 요약 dict 반환. 실행 중 예외는 status=failed 기록 후 전파."""
    stage = on_stage or (lambda _s: None)
    root = Path(root) if root else render.PROJECT_ROOT
    markdown_path = Path(markdown_path)

    # pre-flight (job 디렉터리를 만들기 전에 실패)
    render.ensure_ffmpeg_available()
    render.ensure_remotion_available(root)
    eleven_key = env.require_elevenlabs_key()
    openai_key = env.get_openai_key()

    job_id = state.new_job_id()
    job_dir = Path(jobs_root) / job_id
    for sub in JOB_SUBDIRS:
        (job_dir / sub).mkdir(parents=True, exist_ok=True)
    paths = {
        "source": job_dir / "inputs" / "source.md",
        "audio": job_dir / "audio" / "narration.mp3",
        "words": job_dir / "transcripts" / "words.json",
        "logs": job_dir / "logs",
        "edit": job_dir / "edit",
        "final": job_dir / "edit" / "final.mp4",
    }

    def advance(status: str, **fields: Any) -> None:
        state.write_status(job_dir, status, **fields)
        stage(status)

    advance(
        "created",
        job_id=job_id,
        config=config.model_dump(),
        markdown_input=str(markdown_path.resolve()),
        engine=config.engine,
    )

    try:
        return _run_steps(
            job_id=job_id,
            job_dir=job_dir,
            paths=paths,
            config=config,
            markdown_path=markdown_path,
            model=model,
            output_path=output_path,
            eleven_key=eleven_key,
            openai_key=openai_key,
            root=root,
            advance=advance,
            stage=stage,
        )
    except Exception as exc:
        current = state.read_status(job_dir).get("status")
        if current not in state.TERMINAL:
            state.write_status(job_dir, "failed", error=f"{type(exc).__name__}: {exc}", failed_after=current)
            stage("failed")
        raise


def _run_steps(
    *,
    job_id: str,
    job_dir: Path,
    paths: dict[str, Path],
    config: JobConfig,
    markdown_path: Path,
    model: str,
    output_path: Path | None,
    eleven_key: str,
    openai_key: str | None,
    root: Path,
    advance: Callable[..., None],
    stage: OnStage,
) -> dict[str, Any]:
    logs = paths["logs"]
    edit = paths["edit"]

    # [1] script
    markdown = markdown_path.read_text(encoding="utf-8")
    paths["source"].write_text(markdown, encoding="utf-8")
    sb = None
    sb_narration = None
    if storyboard.is_storyboard(markdown):
        sb = storyboard.parse_storyboard(markdown)
        storyboard.write_storyboard_json(sb, job_dir / "inputs" / "storyboard.json")
        sb_narration = storyboard.narration_text(sb)
    script = script_engine.generate_script(
        markdown,
        openai_key,
        model=model,
        show_opening=config.show_opening,
        log_dir=logs,
        storyboard_narration=sb_narration,
    )
    if not script["full_text"].strip():
        raise ValueError("대본이 비어 있습니다 (입력 마크다운에 내레이션할 내용이 없음)")
    script_engine.write_script_outputs(script, job_dir / "inputs")
    advance("script_generated", script_chars=len(script["full_text"]), script_engine=script["plan"]["engine"])

    # [2] TTS
    tts_text = script["tts"]["text"]
    voice.synthesize(tts_text, config.voice_id, paths["audio"], eleven_key, speed=config.voice_speed, log_dir=logs)
    advance("voice_generated")

    # [3] Scribe → words.json (단일 진실원), [4] 숫자·약어 표시 보정 (timing 유지)
    audio_ms = render.get_audio_duration_ms(paths["audio"])
    words_doc = transcript.transcribe(
        paths["audio"],
        eleven_key,
        audio_duration_ms=audio_ms,
        language=config.language,
        raw_log_path=logs / "scribe_raw.json",
    )
    words_doc = numeric_display.apply_numeric_display_overrides(words_doc, script["full_text"])
    _write_json(paths["words"], words_doc)
    words = words_doc["words"]
    if not words:
        raise ValueError("Scribe 결과에 단어가 없습니다")
    advance("transcribed", audio_duration_ms=audio_ms, word_count=len(words))

    # [5] visual cue planning
    opening_ms = opening.opening_duration_ms(words) if config.show_opening else 0
    if sb is not None:
        segments = _storyboard_segments(sb, words, opening_ms)
        _write_json(edit / "storyboard_segments.json", segments)
    else:
        segments = caption_plan.build_caption_line_segments(words, config.chunk_size, skip_until_ms=opening_ms)
    if segments:
        _write_json(edit / "caption_segments.json", segments)

    visual_mode = config.visual_mode
    emoticon_cues: list[dict[str, Any]] | None = None
    if visual_mode == "photo":
        try:
            emoticon_cues = photo_engine.plan_photo_cues(
                words,
                job_id=job_id,
                api_key=openai_key or "",
                chunk_size=config.chunk_size,
                skip_until_ms=opening_ms,
                segments=segments,
                root=root,
                on_stage=stage,
                log_dir=logs,
            )
            _write_json(edit / "photo_cues.json", emoticon_cues)
        except photo_engine.PhotoEngineError as exc:
            _write_json(
                logs / "photo_fallback.json",
                {"reason": str(exc), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            )
            stage("photo_fallback")
            visual_mode = "emoticon"
            emoticon_cues = None
    if emoticon_cues is None:
        emoticon_cues = emoticon_map.plan_cues(words, segments=segments or None)
        _write_json(edit / "emoticon_cues.json", emoticon_cues)

    number_cards = data_extract.plan_number_cards(script["full_text"], audio_ms)
    if number_cards:
        _write_json(edit / "number_cards.json", number_cards)
    logo_cues = emoticon_map.plan_company_logo_cues(words)
    if logo_cues:
        _write_json(edit / "company_logo_cues.json", logo_cues)
    highlights = emoticon_map.all_highlight_keywords(words)

    # [6] subtitled — Remotion props 확정 (자막 합성은 Remotion 단독 책임)
    props = render.build_props(
        job_id,
        audio_ms,
        bg_color=config.bg_color,
        chunk_size=config.chunk_size,
        emoticon_cues=emoticon_cues,
        caption_segments=segments,
        company_logo_cues=logo_cues,
        number_cards=number_cards,
        highlight_keywords=highlights,
        opening_text=script["opening"]["visual"],
        opening_duration_ms=opening_ms,
        show_opening=config.show_opening,
        cta_text=CTA_TEXT[config.language],
        show_outro=config.show_outro,
    )
    advance("subtitled", visual_mode=visual_mode)

    # [7] render
    render.render_remotion(job_id, paths["audio"], paths["words"], props, paths["final"], logs / "remotion.log", root=root)
    advance("final_rendered")

    # [8] output copy
    output_copy: Path | None = None
    if output_path is not None:
        output_copy = Path(output_path)
        output_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths["final"], output_copy)

    # [9] QC
    used_openai = script["plan"]["engine"] == "openai"
    report = qc.run_qc(
        job_dir=job_dir,
        audio_path=paths["audio"],
        final_mp4=paths["final"],
        words_doc=words_doc,
        cost_inputs={
            "tts_chars": len(tts_text),
            "openai_input_chars": len(script_engine.SYSTEM_PROMPT) + len(markdown) if used_openai else 0,
            "openai_output_chars": len(script["full_text"]) if used_openai else 0,
        },
        audio_duration_fn=render.get_audio_duration_ms,
        video_info_fn=render.get_video_info,
    )
    qc_rel = str(job_dir / "qc_report.json")
    final_status = "qc_passed" if report["passed"] else "qc_failed"
    advance(
        final_status,
        qc_report=qc_rel,
        qc_passed=report["passed"],
        output_copy=str(output_copy) if output_copy else None,
    )
    return {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "status": final_status,
        "final_mp4": str(paths["final"]),
        "output_copy": str(output_copy) if output_copy else None,
        "qc_report": qc_rel,
        "visual_mode": visual_mode,
    }
