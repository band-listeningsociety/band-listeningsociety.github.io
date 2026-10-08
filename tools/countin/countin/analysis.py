"""silencedetect 기반 분석: 첫 소리 시점(S)과 BPM 추정.

librosa 같은 무거운 의존성 없이, ffmpeg silencedetect의 silence_end(= 소리 시작) 시점들로 박자 간격을 추정한다.
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .runner import StepError, run

STEP = "분석(silencedetect)"

_EVENT = re.compile(r"silence_(start|end):\s*(-?[0-9.]+)")

# 박자 간격 후보 범위: 0.3~1.0초 (60~200 BPM)
BEAT_MIN, BEAT_MAX = 0.3, 1.0
# 1차 범위에서 간격이 부족할 때 쓰는 확장 범위(8분음표/2분음표 위주 패턴). 결과는 60~200으로 접는다.
WIDE_MIN, WIDE_MAX = 0.15, 2.0
BPM_MIN, BPM_MAX = 60.0, 200.0
CLUSTER_TOL = 0.15      # 중앙값 ±15%
MIN_INTERVALS = 4       # 사용된 간격이 이보다 적으면 불확실
MAX_REL_STD = 0.10      # 표준편차/평균이 이보다 크면 불확실


class BpmUncertain(Exception):
    pass


def parse_silencedetect(stderr: str) -> List[float]:
    """ffmpeg silencedetect 출력에서 소리 시작 시점 리스트를 만든다.

    파일이 무음 없이 바로 소리로 시작하면(첫 이벤트가 0초 무음이 아니면) 0.0을 첫 시점으로 넣는다.
    """
    events: List[Tuple[str, float]] = [(k, float(v)) for k, v in _EVENT.findall(stderr)]
    onsets: List[float] = []
    if not events or not (events[0][0] == "start" and events[0][1] <= 0.001):
        onsets.append(0.0)
    onsets += [max(0.0, t) for k, t in events if k == "end"]
    return onsets


def detect_onsets(path: Path, noise_db: float, min_silence: float = 0.05) -> List[float]:
    proc = run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        STEP, capture=True,
        hint="입력 오디오를 읽지 못했습니다. 파일 경로와 형식을 확인하세요.",
    )
    return parse_silencedetect(proc.stderr)


def _cluster(intervals: Sequence[float]) -> List[float]:
    med = statistics.median(intervals)
    return [d for d in intervals if abs(d - med) <= med * CLUSTER_TOL]


def estimate_bpm(onsets: Sequence[float], window: float = 20.0) -> Dict:
    """소리 시작 시점 리스트로부터 BPM을 추정한다.

    1) 첫 소리부터 window초 안의 시점만 사용
    2) 인접 간격 중 0.3~1.0초(60~200 BPM)만 후보
    3) 중앙값 ±15% 안의 간격만 평균 → BPM = 60 / 평균
    4) 간격이 4개 미만이거나 표준편차가 평균의 10%를 넘으면 BpmUncertain
    1차 범위에서 간격이 부족하면 확장 범위(0.15~2.0초)로 다시 시도하고 60~200 BPM으로 접는다.
    """
    pts = sorted(onsets)
    if not pts:
        raise BpmUncertain("소리 시작 시점을 하나도 찾지 못했습니다.")
    start = pts[0]
    pts = [t for t in pts if t - start <= window]
    diffs = [b - a for a, b in zip(pts, pts[1:])]

    notes: List[str] = []
    cand = [d for d in diffs if BEAT_MIN <= d <= BEAT_MAX]
    used = _cluster(cand) if cand else []
    if len(used) < MIN_INTERVALS:
        wide = [d for d in diffs if WIDE_MIN <= d <= WIDE_MAX]
        if len(wide) >= MIN_INTERVALS:
            used = _cluster(wide)
            notes.append(f"0.3~1.0초 범위의 간격이 부족해 확장 범위({WIDE_MIN}~{WIDE_MAX}초)를 사용했습니다.")

    if len(used) < MIN_INTERVALS:
        raise BpmUncertain(f"규칙적인 박자 간격이 {len(used)}개뿐입니다(최소 {MIN_INTERVALS}개 필요).")

    mean = statistics.fmean(used)
    std = statistics.pstdev(used)
    if std > mean * MAX_REL_STD:
        raise BpmUncertain(
            f"간격의 편차가 큽니다(표준편차 {std:.4f}초 / 평균 {mean:.4f}초 = {std / mean:.0%}, 허용 {MAX_REL_STD:.0%})."
        )

    raw = 60.0 / mean
    bpm = raw
    while bpm < BPM_MIN:
        bpm *= 2
    while bpm > BPM_MAX:
        bpm /= 2
    if abs(bpm - raw) > 1e-9:
        notes.append(f"더블/하프 템포 의심: {raw:.1f} BPM → {bpm:.1f} BPM으로 보정했습니다.")

    return {
        "bpm": round(bpm, 1),
        "bpm_int": int(round(bpm)),
        "raw_bpm": round(raw, 1),
        "mean_interval": round(mean, 5),
        "std_interval": round(std, 5),
        "intervals_used": [round(d, 4) for d in used],
        "onsets_window": [round(t, 4) for t in pts],
        "notes": notes,
    }


def first_sound(onsets: Sequence[float]) -> float:
    if not onsets:
        raise StepError(STEP, "소리 시작 시점을 찾지 못했습니다.",
                        "--noise-db 값을 -50 등으로 낮추거나 --trim-start에 초 단위 값을 직접 지정하세요.")
    return min(onsets)


def peak_db(path: Path) -> Optional[float]:
    """전체 피크 레벨(dBFS). 0 이상이면 최종 인코딩에서 클리핑된다."""
    proc = run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "astats=measure_perchannel=none:measure_overall=Peak_level", "-f", "null", "-"],
        STEP, capture=True, quiet=True,
    )
    vals = re.findall(r"Peak level dB:\s*(-?[0-9.]+|-inf)", proc.stderr)
    if not vals or vals[-1] == "-inf":
        return None
    return float(vals[-1])
