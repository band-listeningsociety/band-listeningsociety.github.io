"""yt-dlp 다운로드.

과거 문제: -f "b" / -f 140 같은 형식 지정은 'Requested format is not available'이나 403을 냈다.
→ 형식 옵션 없이 받고 --remux-video mp4로 mp4를 보장한다.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from .runner import StepError, info, run
from .workspace import video_id_from_url

STEP = "다운로드(yt-dlp)"


def _hint(stderr: str, cookies: Optional[str]) -> str:
    lines = []
    low = stderr.lower()
    if "403" in stderr or "sign in" in low or "confirm you" in low or "bot" in low:
        lines.append("- 로그인/봇 확인이 필요한 경우가 많습니다. 브라우저 쿠키를 사용해 보세요:")
        lines.append("    --cookies-from-browser chrome   (또는 safari, firefox)")
        if cookies:
            lines.append(f"  (현재 {cookies} 쿠키를 사용 중입니다. 다른 브라우저로 바꾸거나 그 브라우저에서 YouTube에 로그인하세요.)")
    if "requested format" in low:
        lines.append("- 형식 지정 오류입니다. countin은 형식 옵션(-f)을 쓰지 않으므로 yt-dlp를 최신으로 업데이트해 보세요: yt-dlp -U")
    lines.append("- YouTube는 JS 챌린지 해결용 런타임(Deno)이 필요할 수 있습니다:")
    lines.append("    설치: curl -fsSL https://deno.land/install.sh | sh   (안내: https://github.com/yt-dlp/yt-dlp/wiki/EJS)")
    lines.append("- yt-dlp 업데이트: yt-dlp -U   (공식 바이너리로 설치한 경우)")
    lines.append("- 정식 음원 파일이 있으면 --input-audio <파일>로 다운로드 단계를 건너뛸 수 있습니다(음질도 가장 좋음).")
    return "\n".join(lines)


def resolve_id(url: str, cookies: Optional[str]) -> str:
    vid = video_id_from_url(url)
    if vid:
        return vid
    cmd = ["yt-dlp", "--no-playlist", "--skip-download", "--print", "id"]
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    proc = run(cmd + [url], STEP, capture=True, hint=_hint("", cookies))
    vid = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout.strip() else ""
    if not vid:
        raise StepError(STEP, "영상 ID를 알아내지 못했습니다.", _hint(proc.stderr, cookies))
    return vid


def find_source(root: Path) -> Optional[Path]:
    for ext in ("mp4", "mkv", "webm", "m4a", "mov"):
        p = root / f"source.{ext}"
        if p.exists():
            return p
    return None


def download(url: str, root: Path, cookies: Optional[str], resume: bool) -> Path:
    existing = find_source(root)
    if resume and existing:
        info(f"--resume: 기존 영상을 사용합니다 → {existing.name}")
        return existing

    cmd: List[str] = [
        "yt-dlp",
        "--no-playlist",
        "--remux-video", "mp4",
        # 오디오 코덱이 mp4와 맞지 않아 mkv로 합쳐지는 경우 대비
        "--postprocessor-args", "VideoRemuxer:-c:a aac",
        # 병합 전 원본 오디오 스트림(f251.webm 등)을 남겨 둔다 → 추가 손실 없이 오디오 추출에 사용
        "-k",
        "--force-overwrites",
        "-o", str(root / "source.%(ext)s"),
    ]
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    cmd.append(url)
    try:
        run(cmd, STEP, tee_stderr=True)
    except StepError as e:
        raise StepError(STEP, e.message, _hint(getattr(e, "stderr", ""), cookies))

    src = find_source(root)
    if not src:
        raise StepError(STEP, "다운로드는 끝났지만 source.* 파일을 찾지 못했습니다.", _hint("", cookies))
    info(f"다운로드 완료 → {src}")
    return src


def best_audio_file(root: Path, source: Path) -> Path:
    """yt-dlp가 남긴 오디오 전용 원본(source.fNNN.*)이 있으면 그것을, 없으면 source 파일을 쓴다."""
    for p in sorted(root.glob("source.f*.*")):
        if p.suffix in (".part", ".ytdl"):
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(p)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        kinds = set(r.stdout.split())
        if kinds == {"audio"}:
            return p
    return source
