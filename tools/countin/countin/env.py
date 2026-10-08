"""실행 환경 점검: yt-dlp, ffmpeg, ffprobe, demucs."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional

from .runner import StepError, info, warn

# 직접 설치한 정적 바이너리가 있는 흔한 위치. PATH에 없으면 보충한다.
EXTRA_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")]

HINT_YTDLP = (
    "yt-dlp가 없습니다. 공식 바이너리를 직접 내려받아 설치하세요 (brew install은 의존성 소스 빌드로 실패할 수 있어 권장하지 않음):\n"
    "  macOS : curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o /opt/homebrew/bin/yt-dlp\n"
    "          chmod +x /opt/homebrew/bin/yt-dlp\n"
    "  Linux : curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o ~/.local/bin/yt-dlp && chmod +x ~/.local/bin/yt-dlp\n"
    "  (정식 음원을 --input-audio로 직접 지정하면 yt-dlp 없이도 실행됩니다.)"
)
HINT_FFMPEG = (
    "ffmpeg/ffprobe가 없습니다. 정적 빌드 바이너리를 내려받아 PATH 폴더(예: /opt/homebrew/bin)에 넣으세요 (brew install 비권장):\n"
    "  macOS arm64 : https://ffmpeg.martin-riedl.de  (ffmpeg, ffprobe 둘 다 받기)\n"
    "  macOS intel : https://evermeet.cx/ffmpeg/\n"
    "  Linux       : https://johnvansickle.com/ffmpeg/  또는 배포판 패키지(apt install ffmpeg)\n"
    "  설치 후: chmod +x /opt/homebrew/bin/ffmpeg /opt/homebrew/bin/ffprobe\n"
    "  macOS에서 '확인되지 않은 개발자' 경고가 나면: xattr -d com.apple.quarantine /opt/homebrew/bin/ffmpeg /opt/homebrew/bin/ffprobe"
)
HINT_DEMUCS = (
    "demucs를 실행할 수 있는 파이썬을 찾지 못했습니다.\n"
    "  권장: 프로젝트 venv에 설치 (Python 3.10~3.12 권장, 3.9도 동작)\n"
    "    python3 -m venv .venv && source .venv/bin/activate\n"
    "    pip install -r requirements.txt\n"
    "  이미 다른 파이썬에 설치했다면(예: pip install --user) 그 인터프리터를 지정하세요:\n"
    "    --demucs-python /usr/bin/python3   또는   export COUNTIN_DEMUCS_PYTHON=/usr/bin/python3\n"
    "  주의: 'demucs' 명령이 PATH에 없어도 됩니다. countin은 항상 '<python> -m demucs'로 호출합니다."
)


def _ensure_path() -> None:
    parts = os.environ.get("PATH", "").split(os.pathsep)
    added = [d for d in EXTRA_BIN_DIRS if os.path.isdir(d) and d not in parts]
    if added:
        os.environ["PATH"] = os.pathsep.join(parts + added)


def find_tool(name: str) -> Optional[str]:
    _ensure_path()
    return shutil.which(name)


def _python_has_module(python: str, module: str) -> bool:
    try:
        r = subprocess.run(
            [python, "-c", f"import {module}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_demucs_python(explicit: Optional[str]) -> Optional[str]:
    """demucs를 import할 수 있는 파이썬 인터프리터를 찾는다."""
    candidates: List[str] = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("COUNTIN_DEMUCS_PYTHON")
    if env:
        candidates.append(env)
    candidates.append(sys.executable)
    for name in ("python3", "python3.12", "python3.11", "python3.10", "python3.9"):
        p = shutil.which(name)
        if p:
            candidates.append(p)
    candidates.append("/usr/bin/python3")

    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if _python_has_module(c, "demucs"):
            return c
        if explicit and c == explicit:
            warn(f"--demucs-python {explicit} 에서 demucs를 import할 수 없습니다. 다른 후보를 찾습니다.")
    return None


def check(need_ytdlp: bool, need_demucs: bool, demucs_python: Optional[str]) -> Optional[str]:
    """필요한 도구를 점검한다. demucs 파이썬 경로를 반환(필요 없으면 None)."""
    problems = []
    for tool in ("ffmpeg", "ffprobe"):
        path = find_tool(tool)
        if path:
            info(f"{tool}: {path}")
        else:
            problems.append(HINT_FFMPEG)
            break
    else:
        enc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        ).stdout
        if "libmp3lame" not in enc:
            problems.append("ffmpeg에 libmp3lame(mp3 인코더)이 없습니다. libmp3lame이 포함된 정적 빌드로 교체하세요.\n" + HINT_FFMPEG)

    if need_ytdlp:
        path = find_tool("yt-dlp")
        if path:
            info(f"yt-dlp: {path}")
        else:
            problems.append(HINT_YTDLP)

    py = None
    if need_demucs:
        py = find_demucs_python(demucs_python)
        if py:
            info(f"demucs: {py} -m demucs")
        else:
            problems.append(HINT_DEMUCS)

    if problems:
        raise StepError("환경 점검", "필요한 도구가 없습니다.", "\n\n".join(problems))
    return py
