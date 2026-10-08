"""곡별 작업 폴더: output/<id>/{source.mp4, song.wav, stems/, mix.wav, final.mp3, analysis.json}"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

PARTS = ["vocals", "drums", "bass", "guitar", "piano", "other"]

_YT_ID = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})")


def video_id_from_url(url: str) -> Optional[str]:
    m = _YT_ID.search(url)
    return m.group(1) if m else None


def local_id(path: Path) -> str:
    """--input-audio 파일용 작업 폴더 이름(경로+크기 기반 해시, 한글 파일명 회피)."""
    st = path.stat()
    h = hashlib.sha1(f"{path.resolve()}|{st.st_size}".encode("utf-8")).hexdigest()[:10]
    return f"local-{h}"


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    @property
    def song_wav(self) -> Path:
        return self.root / "song.wav"

    @property
    def stems_dir(self) -> Path:
        return self.root / "stems"

    @property
    def mix_wav(self) -> Path:
        return self.root / "mix.wav"

    @property
    def analysis_json(self) -> Path:
        return self.root / "analysis.json"

    def final(self, ext: str) -> Path:
        return self.root / f"final.{ext}"

    @property
    def meta_json(self) -> Path:
        return self.root / "meta.json"

    @property
    def preview_mp3(self) -> Path:
        return self.root / "preview.mp3"

    def read_json(self, path: Path) -> Optional[Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_name(name: str) -> str:
    """파일명에 쓸 수 없는 문자(/, :)만 바꾼다. 한글/공백/괄호는 그대로."""
    return re.sub(r"[/:]", "_", name).strip()


def export(out_root: Path, name: str, finals: List[Path], stems: Dict[str, Path],
           parts: List[str], countin: bool) -> List[Path]:
    """이름 붙인 결과물을 out_root/<name>/에 복사한다.

    <name>(countin+vocals+drums).mp3  최종 결과 (카운트인 없으면 countin+ 생략)
    <name>(vocals).mp3 ...            파트별 스템
    """
    dest = out_root / name
    dest.mkdir(parents=True, exist_ok=True)
    tag = "+".join((["countin"] if countin else []) + parts)
    copies = [(f, dest / f"{name}({tag}){f.suffix}") for f in finals]
    copies += [(stems[p], dest / f"{name}({p}){stems[p].suffix}") for p in PARTS if p in stems]
    for src, dst in copies:
        shutil.copy2(src, dst)
    return [dst for _, dst in copies]
