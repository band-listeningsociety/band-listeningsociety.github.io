"""CLI 진입점: python -m countin "URL" [옵션]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from . import analysis, audio, download, env, mix, separate
from .runner import StepError, info, stage, warn
from .workspace import PARTS, Workspace, clean_name, export, local_id

TOTAL_STAGES = 6


def _bpm_arg(v: str):
    if v.lower() == "auto":
        return "auto"
    try:
        f = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError("--bpm은 숫자 또는 auto여야 합니다.")
    if not 20 <= f <= 400:
        raise argparse.ArgumentTypeError("--bpm은 20~400 범위여야 합니다.")
    return f


def _trim_arg(v: str):
    if v.lower() == "auto":
        return "auto"
    try:
        f = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError("--trim-start는 auto 또는 초 단위 숫자여야 합니다.")
    if f < 0:
        raise argparse.ArgumentTypeError("--trim-start는 0 이상이어야 합니다.")
    return f


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="countin",
        description="곡을 분해하고, 원하는 파트만 골라 카운트인을 붙여 연습용 트랙으로 만드는 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            '  python -m countin "https://youtube.com/watch?v=XXXX" --exclude guitar bass --bpm 116 --song-sticks 2\n'
            '  python -m countin "URL" --resume --preview --trim-start 0.68\n'
            "  python -m countin --input-audio song.flac --include drums vocals --bpm auto\n"
        ),
    )
    p.add_argument("url", nargs="?", help="YouTube URL (--input-audio를 쓰면 생략 가능)")
    p.add_argument("--version", action="version", version=f"countin {__version__}")

    g = p.add_argument_group("입력")
    g.add_argument("--input-audio", type=Path, metavar="PATH",
                   help="정식 음원(FLAC/mp3 320 등)을 직접 지정. 다운로드를 건너뜀 (가장 큰 음질 개선)")
    g.add_argument("--cookies-from-browser", choices=["chrome", "safari", "firefox", "edge", "brave"],
                   help="yt-dlp가 403/로그인 오류를 낼 때 브라우저 쿠키 사용")

    g = p.add_argument_group("파트 선택")
    sel = g.add_mutually_exclusive_group()
    sel.add_argument("--exclude", nargs="+", choices=PARTS, metavar="PART",
                     help=f"뺄 파트 (기본: guitar bass). 선택지: {' '.join(PARTS)}")
    sel.add_argument("--include", nargs="+", choices=PARTS, metavar="PART", help="남길 파트만 지정")
    g.add_argument("--volume", type=float, default=0.8,
                   help="믹스 볼륨 배율 (기본 0.8). 소리가 깨지면(clipping) 낮추세요")

    g = p.add_argument_group("카운트인")
    g.add_argument("--bpm", type=_bpm_arg, default="auto", help="BPM 숫자 또는 auto (기본 auto)")
    g.add_argument("--bpm-source", choices=["mix", "drums"], default="mix",
                   help="BPM 자동 추정에 쓸 오디오 (기본 mix). 앞부분이 멜로디로 시작해 불확실하면 drums")
    g.add_argument("--count-total", type=int, default=8,
                   help="곡 안의 스틱 카운트를 포함한 총 카운트 수 (기본 8)")
    g.add_argument("--song-sticks", type=int, default=0,
                   help="곡 안에 이미 들어 있는 스틱 카운트 수 (기본 0). 앞에 붙는 틱 = count-total - song-sticks")
    g.add_argument("--count-in", type=int, default=None, metavar="N",
                   help="앞에 붙일 틱 개수를 직접 지정 (count-total/song-sticks 무시). 0이면 카운트인 생략")
    g.add_argument("--tick-freq", type=float, default=1500.0, help="틱 주파수 Hz (기본 1500)")
    g.add_argument("--tick-dur", type=float, default=0.05, help="틱 길이 초 (기본 0.05)")
    g.add_argument("--tick-db", type=float, default=-6.0, help="틱 크기 dBFS (기본 -6)")

    g = p.add_argument_group("곡 시작 맞추기")
    g.add_argument("--trim-start", type=_trim_arg, default="auto",
                   help="앞 무음 자르기: auto(첫 소리 자동 감지) 또는 초 단위 값 (기본 auto)")
    g.add_argument("--trim-offset", type=float, default=0.0,
                   help="trim-start에 더할 보정값(초, 음수 가능). 박이 어긋나면 0.01~0.02 단위로 조정")
    g.add_argument("--noise-db", type=float, default=-40.0,
                   help="silencedetect 무음 기준 dB (기본 -40). 감지가 부정확하면 -50 등으로")

    g = p.add_argument_group("품질/출력")
    g.add_argument("--quality", choices=["normal", "high", "max"], default="high",
                   help="normal: demucs 기본 / high(기본): shifts 2 / max: shifts 4, overlap 0.25, FLAC 스템")
    g.add_argument("--lossless", action="store_true", help="final.flac도 함께 출력")
    g.add_argument("--name", metavar="아티스트-곡명",
                   help='결과물 파일명 (예: "Franz Ferdinand-No You Girls"). '
                        "<out>/<name>/에 <name>(countin+파트).mp3와 파트별 스템을 저장. 한 번 지정하면 기억됨")
    g.add_argument("--out", type=Path, default=Path("./output"), help="출력 루트 폴더 (기본 ./output)")
    g.add_argument("--preview", action="store_true", help="앞부분만 preview.mp3로 출력해 박 맞춤 확인")
    g.add_argument("--preview-sec", type=float, default=10.0, help="미리듣기 길이 초 (기본 10)")

    g = p.add_argument_group("실행 제어")
    g.add_argument("--resume", action="store_true",
                   help="이미 있는 중간 산출물(다운로드/추출/스템/분석)을 재사용")
    g.add_argument("--redo-stems", action="store_true", help="스템 분리를 다시 실행 (품질 변경 시)")
    g.add_argument("--demucs-python", metavar="PYTHON",
                   help="demucs가 설치된 파이썬 경로 (환경변수 COUNTIN_DEMUCS_PYTHON도 가능)")
    g.add_argument("--device", choices=["cpu", "mps", "cuda"], help="demucs 실행 장치 (기본: demucs 자동 선택. mps는 htdemucs_6s에서 실패함)")
    return p


def selected_parts(args) -> List[str]:
    if args.include:
        parts = [p for p in PARTS if p in args.include]
    else:
        excl = args.exclude if args.exclude is not None else ["guitar", "bass"]
        parts = [p for p in PARTS if p not in excl]
    if not parts:
        raise StepError("옵션 확인", "선택된 파트가 없습니다.", "--include 또는 --exclude를 확인하세요.")
    return parts


def count_in_ticks(args) -> int:
    if args.count_in is not None:
        n = args.count_in
    else:
        n = args.count_total - args.song_sticks
    if n < 0:
        raise StepError("옵션 확인",
                        f"앞에 붙일 틱 수가 음수입니다 (count-total {args.count_total} - song-sticks {args.song_sticks}).",
                        "--song-sticks가 --count-total보다 클 수 없습니다.")
    return n


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _main(args)
    except StepError as e:
        print(f"\n[countin] 실패한 단계: {e.step}", file=sys.stderr)
        print(f"[countin] {e.message}", file=sys.stderr)
        if e.hint:
            print("\n[countin] 대응 방법:\n" + e.hint, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[countin] 중단되었습니다. --resume으로 이어서 실행할 수 있습니다.", file=sys.stderr)
        return 130


def _main(args) -> int:
    if not args.url and not args.input_audio:
        raise StepError("옵션 확인", "YouTube URL 또는 --input-audio 중 하나가 필요합니다.",
                        '예: python -m countin "https://youtube.com/watch?v=XXXX"')
    if args.input_audio and not args.input_audio.exists():
        raise StepError("옵션 확인", f"입력 파일이 없습니다: {args.input_audio}", "경로를 따옴표로 감싸 다시 지정하세요.")

    parts = selected_parts(args)
    ticks = count_in_ticks(args)

    # ---------- 1. 환경 점검 ----------
    stage(1, TOTAL_STAGES, "환경 점검")
    from_youtube = args.input_audio is None
    demucs_py = env.check(need_ytdlp=from_youtube, need_demucs=True, demucs_python=args.demucs_python)

    # ---------- 2. 원본 준비 ----------
    stage(2, TOTAL_STAGES, "원본 준비")
    if from_youtube:
        vid = download.resolve_id(args.url, args.cookies_from_browser)
        ws = Workspace(args.out / vid)
        info(f"작업 폴더: {ws.root}")
        src = download.download(args.url, ws.root, args.cookies_from_browser, args.resume)
        audio_src = download.best_audio_file(ws.root, src)
    else:
        ws = Workspace(args.out / local_id(args.input_audio))
        info(f"작업 폴더: {ws.root}  (입력: {args.input_audio})")
        audio_src = args.input_audio
        info("정식 음원을 사용합니다. 유튜브 오디오보다 분리 품질과 최종 음질이 좋아집니다.")
    audio.report_quality(audio_src, from_youtube)

    meta = ws.read_json(ws.meta_json) or {}
    if args.name:
        meta["name"] = clean_name(args.name)
        ws.write_json(ws.meta_json, meta)
    name = meta.get("name")
    if name:
        info(f"곡 이름: {name}")

    # ---------- 3. 오디오 추출 ----------
    stage(3, TOTAL_STAGES, "오디오 추출 → song.wav")
    audio.extract(audio_src, ws.song_wav, resume=args.resume, high_res=args.quality == "max")

    # ---------- 4. 스템 분리 ----------
    stage(4, TOTAL_STAGES, f"스템 분리 (htdemucs_6s, quality={args.quality})")
    assert demucs_py is not None
    stems = separate.separate(ws, demucs_py, args.quality, args.device,
                              resume=args.resume, redo=args.redo_stems)

    # ---------- 5. 믹스 + 분석 ----------
    stage(5, TOTAL_STAGES, "파트 믹스 + 분석")
    sid = separate.stems_id(ws)
    mix_key = {"parts": parts, "volume": args.volume, "stems": sid}
    mix_meta = ws.root / "mix.json"
    if args.resume and ws.mix_wav.exists() and ws.read_json(mix_meta) == mix_key:
        info(f"--resume: 기존 mix.wav를 사용합니다 ({', '.join(parts)})")
    else:
        mix.build_mix(stems, parts, args.volume, ws.mix_wav)
        ws.write_json(mix_meta, mix_key)

    peak = analysis.peak_db(ws.mix_wav)
    if peak is not None:
        info(f"믹스 피크 레벨: {peak:.2f} dBFS")
        if peak > -0.1:
            suggest = args.volume * 10 ** (-(peak + 1.0) / 20.0)
            warn(f"믹스가 0 dBFS를 넘어 최종 mp3에서 소리가 깨질(clipping) 수 있습니다. "
                 f"--volume {suggest:.2f} 이하로 다시 실행하세요.")

    trim, bpm, analysis_data = _analyze(args, ws, stems, parts, sid, ticks)

    # ---------- 6. 카운트인 + 출력 ----------
    stage(6, TOTAL_STAGES, "카운트인 합성 + 출력")
    countin = None
    if ticks > 0:
        countin = mix.CountIn(count=ticks, bpm=bpm, freq=args.tick_freq,
                              tick_dur=args.tick_dur, tick_db=args.tick_db)
        info(f"카운트인: {ticks}번 (BPM {bpm:g}, 간격 {countin.interval:.5f}초 = {countin.beat_samples}샘플, "
             f"aloop loop={countin.loop}, 길이 {countin.duration:.3f}초)")
        if args.count_in is None:
            info(f"  총 카운트 {args.count_total} = 앞 틱 {ticks} + 곡 안 스틱 {args.song_sticks}")
    else:
        info("카운트인 생략 (틱 0번)")
    info(f"곡 앞 트림: {trim:.3f}초")

    if args.preview:
        mix.render(ws.mix_wav, trim, countin, [ws.preview_mp3], preview_sec=args.preview_sec)
        info(f"미리듣기 완료 → {ws.preview_mp3}")
        info("박이 어긋나면 --trim-start 값을 0.01~0.02초 단위로 바꿔 --resume --preview로 다시 확인하세요.")
        outputs = [ws.preview_mp3]
    else:
        outputs = [ws.final("mp3")]
        if args.lossless:
            outputs.append(ws.final("flac"))
        mix.render(ws.mix_wav, trim, countin, outputs)

    analysis_data["render"] = {
        "parts": parts, "trim_start_used": round(trim, 4),
        "count_in": ticks, "bpm_used": bpm,
        "beat_samples": countin.beat_samples if countin else None,
        "outputs": [o.name for o in outputs],
    }
    ws.write_json(ws.analysis_json, analysis_data)

    if not args.preview:
        if name:
            outputs = export(args.out, name, outputs, stems, parts, countin=ticks > 0)
        else:
            info('--name "아티스트-곡명"을 주면 결과물과 스템을 그 이름으로 정리해 저장합니다.')

    print()
    for o in outputs:
        info(f"완료 → {o}")
    return 0


def _analyze(args, ws: Workspace, stems, parts, sid: str, ticks: int):
    """첫 소리 시점 S와 BPM을 정한다. silencedetect 결과는 analysis.json에 캐시."""
    need_bpm = ticks > 0 and args.bpm == "auto"
    need_s = args.trim_start == "auto"

    key = {"parts": parts, "volume": args.volume, "noise_db": args.noise_db, "stems": sid}
    cached = ws.read_json(ws.analysis_json) or {}
    data = {"key": key}
    if cached.get("key") == key:
        data.update({k: v for k, v in cached.items() if k in ("onsets_mix", "onsets_drums", "first_sound", "bpm")})
        if data.get("onsets_mix") or data.get("onsets_drums"):
            info("analysis.json의 기존 분석 결과를 재사용합니다.")

    def onsets_for(source: str) -> List[float]:
        k = f"onsets_{source}"
        if k not in data:
            path = ws.mix_wav if source == "mix" else stems["drums"]
            info(f"silencedetect 분석: {path.name} (noise={args.noise_db}dB)")
            data[k] = [round(t, 4) for t in analysis.detect_onsets(path, args.noise_db)]
        return data[k]

    # 첫 소리 시점: 선택한 파트로 만든 믹스 기준
    if need_s:
        s = analysis.first_sound(onsets_for("mix"))
        data["first_sound"] = s
        info(f"첫 소리 시점(자동 감지): {s:.3f}초")
        trim = s + args.trim_offset
    else:
        trim = float(args.trim_start) + args.trim_offset
    if args.trim_offset:
        info(f"trim-offset {args.trim_offset:+.3f}초 적용")
    trim = max(0.0, trim)

    bpm: float = 0.0
    if ticks > 0 and args.bpm != "auto":
        bpm = float(args.bpm)
        info(f"BPM: {bpm:g} (수동 지정)")
    elif need_bpm:
        if args.bpm_source == "drums" and "drums" not in parts:
            info("drums 파트는 믹스에서 빠졌지만 BPM 분석에는 드럼 스템을 사용합니다.")
        onsets = onsets_for(args.bpm_source)
        try:
            est = analysis.estimate_bpm(onsets)
        except analysis.BpmUncertain as e:
            ws.write_json(ws.analysis_json, data)
            hint = "--bpm 숫자를 직접 지정하세요 (예: --bpm 116)."
            if args.bpm_source == "mix":
                hint += "\n또는 드럼 스템으로 분석해 보세요: --bpm-source drums"
            hint += f"\n감지 기준을 바꿔 볼 수도 있습니다: --noise-db -50 (현재 {args.noise_db})"
            raise StepError("BPM 자동 추정", f"추정이 불확실합니다. --bpm 숫자를 직접 지정하세요. ({e})", hint)
        data["bpm"] = {**est, "source": args.bpm_source}
        for n in est["notes"]:
            warn(n)
        info(f"BPM 추정({args.bpm_source}): {est['bpm']} → 사용 {est['bpm_int']} BPM "
             f"(간격 {len(est['intervals_used'])}개, 평균 {est['mean_interval']}초, 표준편차 {est['std_interval']}초)")
        info(f"  사용한 간격: {est['intervals_used']}")
        bpm = float(est["bpm_int"])
    return trim, bpm, data


if __name__ == "__main__":
    sys.exit(main())
