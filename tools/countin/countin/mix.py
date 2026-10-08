"""파트 믹스와 카운트인 합성.

- mix.wav: 선택한 스템을 amix로 합친 무손실 중간 파일(32bit float이라 중간 단계에서 클리핑 없음)
- final  : mix.wav → 앞 무음 트림 → 카운트인 틱과 concat → mp3 320k (손실 인코딩은 이 한 번뿐)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .runner import info, run

SR = 44100
SINE_AMPLITUDE = 0.125  # ffmpeg sine 소스의 기본 진폭(1/8)

STEP_MIX = "파트 믹스(ffmpeg amix)"
STEP_FINAL = "카운트인 합성/인코딩(ffmpeg)"


def build_mix(stems: Dict[str, Path], parts: Sequence[str], volume: float, out_wav: Path) -> None:
    inputs: List[str] = []
    for p in parts:
        inputs += ["-i", str(stems[p])]
    n = len(parts)
    labels = "".join(f"[{i}:a]" for i in range(n))
    if n == 1:
        graph = f"[0:a]volume={volume}[m]"
    else:
        # inputs=N은 선택된 파트 수와 반드시 일치해야 한다
        graph = f"{labels}amix=inputs={n}:normalize=0,volume={volume}[m]"
    tmp = out_wav.with_name(out_wav.stem + ".tmp.wav")
    run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
         "-filter_complex", graph, "-map", "[m]",
         "-ar", str(SR), "-c:a", "pcm_f32le", str(tmp)],
        STEP_MIX,
        hint="스템 파일이 손상되었을 수 있습니다. --redo-stems로 스템 분리를 다시 실행해 보세요.",
    )
    tmp.replace(out_wav)
    info(f"믹스 완료 ({n}개 파트: {', '.join(parts)}, volume={volume}) → {out_wav}")


@dataclass
class CountIn:
    count: int          # 앞에 붙일 틱 개수
    bpm: float
    freq: float = 1500.0
    tick_dur: float = 0.05
    tick_db: float = -6.0

    @property
    def interval(self) -> float:
        """한 박자 간격(초) = 60 / BPM"""
        return 60.0 / self.bpm

    @property
    def beat_samples(self) -> int:
        """한 박자 샘플 수 = 간격 × 44100 (apad 길이와 aloop size에 함께 사용)"""
        return int(round(self.interval * SR))

    @property
    def loop(self) -> int:
        """aloop의 loop 값. 총 틱 횟수 = loop + 1"""
        return self.count - 1

    @property
    def duration(self) -> float:
        return self.count * self.beat_samples / SR

    def filter(self, label: str = "ci") -> str:
        gain = (10 ** (self.tick_db / 20.0)) / SINE_AMPLITUDE
        fade = min(0.005, self.tick_dur / 2)
        return (
            f"sine=frequency={self.freq}:sample_rate={SR}:duration={self.tick_dur},"
            f"afade=t=out:st={self.tick_dur - fade:.4f}:d={fade:.4f},"
            f"volume={gain:.4f},"
            f"aformat=sample_rates={SR}:channel_layouts=stereo,"
            # 틱 하나를 한 박자 길이로 패딩한 뒤, 그 한 박자를 loop번 더 반복
            f"apad=whole_len={self.beat_samples},"
            f"aloop=loop={self.loop}:size={self.beat_samples}"
            f"[{label}]"
        )


def final_graph(trim_start: float, countin: Optional[CountIn]) -> str:
    song = "[0:a]"
    if trim_start > 0:
        song += f"atrim=start={trim_start:.4f},asetpts=PTS-STARTPTS,"
    song += f"aformat=sample_rates={SR}:channel_layouts=stereo"
    if countin is None or countin.count <= 0:
        return song + "[out]"
    return f"{countin.filter('ci')};{song}[song];[ci][song]concat=n=2:v=0:a=1[out]"


def render(mix_wav: Path, trim_start: float, countin: Optional[CountIn],
           outputs: List[Path], preview_sec: Optional[float] = None) -> None:
    """한 번의 ffmpeg 호출로 트림 + 카운트인 + 인코딩. outputs 확장자(.mp3/.flac)에 맞춰 저장."""
    graph = final_graph(trim_start, countin)
    n = len(outputs)
    if n > 1:
        graph += f";[out]asplit={n}" + "".join(f"[o{i}]" for i in range(n))
        labels = [f"[o{i}]" for i in range(n)]
    else:
        labels = ["[out]"]

    cmd: List[str] = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                      "-i", str(mix_wav), "-filter_complex", graph]
    tmps = []
    for label, out in zip(labels, outputs):
        cmd += ["-map", label]
        if preview_sec:
            cmd += ["-t", f"{preview_sec}"]
        if out.suffix == ".flac":
            cmd += ["-c:a", "flac", "-sample_fmt", "s32", "-ar", str(SR)]
        else:
            cmd += ["-c:a", "libmp3lame", "-b:a", "320k", "-ar", str(SR)]
        tmp = out.with_name(out.stem + ".tmp" + out.suffix)
        tmps.append((tmp, out))
        cmd.append(str(tmp))
    run(cmd, STEP_FINAL,
        hint="ffmpeg 버전이 너무 오래되었을 수 있습니다(amix normalize, aloop 필요). 최신 정적 빌드를 사용하세요.")
    for tmp, out in tmps:
        tmp.replace(out)
