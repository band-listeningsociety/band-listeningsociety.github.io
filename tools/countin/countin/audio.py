"""오디오 추출: 원본(영상 또는 정식 음원) → song.wav"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .runner import info, run, warn

STEP = "오디오 추출(ffmpeg)"


def probe_audio(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,bit_rate,sample_rate,channels:format=bit_rate",
         "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
    )
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError:
        return {}
    stream = (data.get("streams") or [{}])[0]
    br = stream.get("bit_rate") or (data.get("format") or {}).get("bit_rate")
    return {
        "codec": stream.get("codec_name"),
        "bit_rate_kbps": round(int(br) / 1000) if br and str(br).isdigit() else None,
        "sample_rate": stream.get("sample_rate"),
        "channels": stream.get("channels"),
    }


LOSSLESS = {"flac", "alac", "wav", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "aiff"}


def report_quality(path: Path, from_youtube: bool) -> None:
    p = probe_audio(path)
    codec = p.get("codec") or "?"
    kbps = p.get("bit_rate_kbps")
    info(f"원본 오디오: {path.name} / 코덱 {codec} / {kbps or '?'} kbps / {p.get('sample_rate') or '?'} Hz")
    if codec in LOSSLESS or (codec or "").startswith("pcm_"):
        return
    if from_youtube:
        warn(
            f"원본이 유튜브 손실 압축 오디오({codec}, 약 {kbps or 128} kbps)입니다. "
            "최종 출력을 320k로 저장해도 원래 없던 정보는 생기지 않습니다. "
            "정식 음원(FLAC 또는 mp3 320)이 있다면 --input-audio로 지정하는 것이 가장 큰 음질 개선입니다."
        )
    elif kbps and kbps < 256:
        warn(f"입력 음원 비트레이트가 {kbps} kbps입니다. 결과 음질은 원본 음질을 넘지 못합니다.")


def extract(src: Path, out_wav: Path, resume: bool, high_res: bool) -> Path:
    if resume and out_wav.exists():
        info(f"--resume: 기존 {out_wav.name}을 사용합니다.")
        return out_wav
    codec = "pcm_s24le" if high_res else "pcm_s16le"
    tmp = out_wav.with_name(out_wav.stem + ".tmp.wav")
    run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", src, "-vn", "-c:a", codec, tmp],
        STEP,
        hint="입력 파일이 손상되었거나 오디오 트랙이 없는지 확인하세요. ffprobe <파일>로 스트림을 확인할 수 있습니다.",
    )
    tmp.replace(out_wav)
    info(f"추출 완료 → {out_wav}")
    return out_wav
