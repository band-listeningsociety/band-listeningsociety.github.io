"""외부 명령 실행과 로그 출력.

모든 명령은 리스트 인자로 전달하고 shell=True를 쓰지 않는다(한글/공백/괄호 파일명 안전).
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from typing import List, Optional, Sequence


class StepError(Exception):
    """단계 실패. step: 단계 이름, hint: 한국어 대응 방법."""

    def __init__(self, step: str, message: str, hint: str = ""):
        super().__init__(message)
        self.step = step
        self.message = message
        self.hint = hint


def info(msg: str) -> None:
    print(f"[countin] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[countin] 경고: {msg}", file=sys.stderr, flush=True)


def stage(num: int, total: int, title: str) -> None:
    print(f"\n=== [{num}/{total}] {title} ===", flush=True)


def show_cmd(cmd: Sequence[str]) -> None:
    print("  $ " + shlex.join(str(c) for c in cmd), flush=True)


def run(
    cmd: Sequence[str],
    step: str,
    hint: str = "",
    capture: bool = False,
    tee_stderr: bool = False,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    """명령 실행.

    capture=True    : stdout/stderr를 모두 받아서 반환(터미널에 출력하지 않음).
    tee_stderr=True : stderr를 터미널에 그대로 보여주면서 동시에 수집(오류 원인 분석용).
    실패하면 StepError를 던진다.
    """
    cmd = [str(c) for c in cmd]
    if not quiet:
        show_cmd(cmd)
    try:
        if capture:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
        elif tee_stderr:
            p = subprocess.Popen(
                cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            )
            lines: List[str] = []
            assert p.stderr is not None
            for line in p.stderr:
                sys.stderr.write(line)
                lines.append(line)
            p.wait()
            proc = subprocess.CompletedProcess(cmd, p.returncode, None, "".join(lines))
        else:
            proc = subprocess.run(cmd)
    except FileNotFoundError:
        raise StepError(step, f"실행 파일을 찾을 수 없습니다: {cmd[0]}", hint)
    if proc.returncode != 0:
        tail = _tail(proc.stderr) if proc.stderr else ""
        msg = f"명령이 실패했습니다 (종료 코드 {proc.returncode})."
        if tail and capture:
            msg += "\n--- 마지막 출력 ---\n" + tail
        err = StepError(step, msg, hint)
        err.stderr = proc.stderr or ""  # type: ignore[attr-defined]
        raise err
    return proc


def _tail(text: Optional[str], n: int = 15) -> str:
    if not text:
        return ""
    return "\n".join(text.strip().splitlines()[-n:])
