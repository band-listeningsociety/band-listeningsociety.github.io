"""Demucs 6파트 스템 분리 (htdemucs_6s).

과거 문제: torchaudio 백엔드 문제로 wav 저장 시 "Couldn't find appropriate backend".
→ 기본은 --mp3 --mp3-bitrate 320, max 품질에서만 soundfile + --flac을 시도하고 실패하면 mp3로 폴백.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from .runner import StepError, info, run, warn
from .workspace import PARTS, Workspace

STEP = "스템 분리(demucs)"
MODEL = "htdemucs_6s"

PRESETS: Dict[str, Dict] = {
    "normal": {"args": [], "format": "mp3"},
    "high": {"args": ["--shifts", "2"], "format": "mp3"},
    "max": {"args": ["--shifts", "4", "--overlap", "0.25"], "format": "flac"},
}

HINT = (
    "- 메모리 부족이면 다른 앱을 닫거나 --quality normal로 다시 시도하세요.\n"
    "- \"Couldn't find appropriate backend\" 오류는 wav/flac 저장 문제입니다. --quality high(mp3 320 저장)로 실행하세요.\n"
    "- \"not supported at the MPS device\" 오류는 htdemucs_6s가 MPS를 지원하지 않아서 납니다. --device cpu로 실행하세요(--resume으로 다운로드 재사용).\n"
    "- 처음 실행 시 모델(htdemucs_6s)을 내려받으므로 인터넷 연결이 필요합니다.\n"
    "- demucs 설치 확인: <python> -m demucs --help"
)


def stem_files(stems_dir: Path) -> Optional[Dict[str, Path]]:
    """6개 스템이 모두 있으면 {part: path} 반환."""
    found = {}
    for part in PARTS:
        for ext in ("flac", "wav", "mp3"):
            p = stems_dir / f"{part}.{ext}"
            if p.exists():
                found[part] = p
                break
    return found if len(found) == len(PARTS) else None


def _ensure_soundfile(python: str) -> bool:
    ok = subprocess.run([python, "-c", "import soundfile"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if ok:
        return True
    info("FLAC 저장을 위해 soundfile을 설치합니다.")
    for extra in ([], ["--user"]):
        cmd = [python, "-m", "pip", "install", *extra, "soundfile"]
        try:
            run(cmd, STEP)
            return True
        except StepError:
            continue
    warn("soundfile 설치에 실패했습니다. mp3 320으로 저장합니다.")
    return False


def _demucs_cmd(python: str, song: Path, out_dir: Path, preset_args: List[str],
                fmt: str, device: Optional[str]) -> List[str]:
    cmd = [python, "-m", "demucs", "-n", MODEL, *preset_args, "-o", str(out_dir)]
    if fmt == "mp3":
        cmd += ["--mp3", "--mp3-bitrate", "320"]
    elif fmt == "flac":
        cmd += ["--flac"]
    if device:
        cmd += ["-d", device]
    cmd.append(str(song))
    return cmd


def separate(ws: Workspace, python: str, quality: str, device: Optional[str],
             resume: bool, redo: bool) -> Dict[str, Path]:
    meta_path = ws.stems_dir / "stems.json"
    existing = stem_files(ws.stems_dir)

    if resume and existing and not redo:
        meta = ws.read_json(meta_path) or {}
        made_with = meta.get("quality")
        if made_with and made_with != quality:
            raise StepError(
                STEP,
                f"기존 스템은 --quality {made_with}로 만들어졌는데 이번에는 --quality {quality}입니다.",
                "품질을 바꾸려면 스템 분리부터 다시 해야 합니다. --redo-stems를 함께 주거나 --resume 없이 실행하세요.\n"
                f"기존 스템을 그대로 쓰려면 --quality {made_with}로 실행하세요.",
            )
        info(f"--resume: 기존 스템을 사용합니다 ({ws.stems_dir}, quality={made_with or '?'})")
        return existing

    # 기존 결과는 덮어쓰기 전에 백업
    if ws.stems_dir.exists() and any(ws.stems_dir.iterdir()):
        backup = ws.root / f"stems_backup_{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copytree(ws.stems_dir, backup)
        info(f"기존 스템을 백업했습니다 → {backup.name}")
        shutil.rmtree(ws.stems_dir)

    preset = PRESETS[quality]
    fmt = preset["format"]
    if fmt == "flac" and not _ensure_soundfile(python):
        fmt = "mp3"

    tmp_out = ws.root / "separated"
    if tmp_out.exists():
        shutil.rmtree(tmp_out)

    info(f"Demucs {MODEL} 실행 (quality={quality}, 저장 형식={fmt}). 곡 길이와 품질에 따라 수 분~수십 분 걸립니다.")
    try:
        run(_demucs_cmd(python, ws.song_wav, tmp_out, preset["args"], fmt, device), STEP, hint=HINT)
    except StepError:
        if fmt != "mp3":
            warn("FLAC 저장에 실패했습니다. mp3 320으로 다시 분리합니다.")
            fmt = "mp3"
            if tmp_out.exists():
                shutil.rmtree(tmp_out)
            run(_demucs_cmd(python, ws.song_wav, tmp_out, preset["args"], fmt, device), STEP, hint=HINT)
        else:
            raise

    result_dir = tmp_out / MODEL / ws.song_wav.stem
    ws.stems_dir.mkdir(parents=True, exist_ok=True)
    for part in PARTS:
        src = result_dir / f"{part}.{fmt}"
        if not src.exists():
            raise StepError(STEP, f"스템 파일이 생성되지 않았습니다: {src}", HINT)
        shutil.move(str(src), str(ws.stems_dir / src.name))
    shutil.rmtree(tmp_out, ignore_errors=True)

    ws.write_json(meta_path, {
        "model": MODEL, "quality": quality, "format": fmt,
        "args": preset["args"], "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    info(f"스템 분리 완료 → {ws.stems_dir} ({fmt})")
    stems = stem_files(ws.stems_dir)
    assert stems is not None
    return stems


def stems_id(ws: Workspace) -> str:
    """스템이 다시 만들어졌는지 판별하기 위한 값(분석 캐시 무효화용)."""
    meta = ws.read_json(ws.stems_dir / "stems.json") or {}
    return f"{meta.get('quality')}|{meta.get('format')}|{meta.get('created')}"
