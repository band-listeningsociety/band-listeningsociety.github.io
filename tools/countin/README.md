# countin

곡을 분해하고, 원하는 파트만 골라 카운트인을 붙여 연습용 트랙으로 만드는 도구

YouTube URL(또는 음원 파일) 하나로 아래 과정을 한 번에 처리합니다.

1. yt-dlp로 다운로드 (mp4)
2. 오디오를 `song.wav`로 추출
3. Demucs(`htdemucs_6s`)로 6파트 분리: vocals, drums, bass, guitar, piano, other
4. 원하는 파트만 골라 믹스 (기본: guitar, bass 제외)
5. 곡 앞 무음을 잘라내고, 박자에 맞춘 카운트인(틱) 삽입
6. 최종 `final.mp3`(320kbps) 출력, 옵션으로 `final.flac`

> 개인 학습/연습용 도구입니다. 저작권이 있는 음원은 개인 사용 범위에서만 사용하고, 결과물을 배포하지 마세요.

---

## 설치

### 1. 외부 도구 (yt-dlp, ffmpeg, ffprobe)

pip가 아니라 **공식/정적 바이너리**로 설치합니다.
Apple Silicon에서 `brew install yt-dlp`/`brew install ffmpeg`는 LLVM·SDL 등을 소스 빌드하다 실패하는 경우가 있어 권장하지 않습니다.

```zsh
# yt-dlp (공식 바이너리)
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o /opt/homebrew/bin/yt-dlp
chmod +x /opt/homebrew/bin/yt-dlp

# ffmpeg, ffprobe (macOS arm64 정적 빌드: https://ffmpeg.martin-riedl.de 에서 둘 다 받기)
#   받은 파일을 /opt/homebrew/bin/ 에 넣고:
chmod +x /opt/homebrew/bin/ffmpeg /opt/homebrew/bin/ffprobe
xattr -d com.apple.quarantine /opt/homebrew/bin/ffmpeg /opt/homebrew/bin/ffprobe 2>/dev/null
```

Linux는 yt-dlp 공식 바이너리와 배포판의 ffmpeg 패키지(또는 johnvansickle.com 정적 빌드)를 쓰면 됩니다.
countin은 시작할 때 이 도구들이 있는지 점검하고, 없으면 설치 방법을 안내합니다.

### 2. countin과 demucs (venv 권장)

countin 자체는 **파이썬 표준 라이브러리만** 사용합니다. 스템 분리에만 `demucs`(PyTorch 포함, 수 GB)가 필요합니다.

```zsh
cd countin
python3.11 -m venv .venv          # 3.10~3.12 권장 (3.9도 동작). python.org 설치본 사용 가능
source .venv/bin/activate
pip install -r requirements.txt    # demucs 4.0.1 + soundfile
python -m countin --help
```

시스템에 파이썬이 3.9뿐이라면 `python3 -m venv .venv`로 만들어도 됩니다.

**이미 demucs를 다른 파이썬에 설치했다면**(예: `pip install --user demucs`) 다시 설치할 필요 없이 그 인터프리터를 지정하면 됩니다.
`demucs` 명령이 PATH에 없어도 괜찮습니다. countin은 항상 `<python> -m demucs`로 호출합니다.

```zsh
python3 -m countin "URL" --demucs-python /usr/bin/python3
# 또는
export COUNTIN_DEMUCS_PYTHON=/usr/bin/python3
```

지정하지 않으면 현재 파이썬 → PATH의 `python3*` → `/usr/bin/python3` 순으로 demucs를 import할 수 있는 인터프리터를 자동으로 찾습니다.

### (선택) `countin` 명령 등록

```zsh
pip install -e .
countin "URL" ...
```

venv 밖에서 `pip install --user -e .`로 설치하면 실행 파일 폴더(예: `~/Library/Python/3.9/bin`)가 PATH에 없어
`zsh: command not found: countin`이 날 수 있습니다. **venv 안에서 설치하거나, 그냥 `python -m countin`을 쓰는 것을 권장합니다.**

---

## 사용법

```zsh
python -m countin "https://youtube.com/watch?v=XXXX" \
  --exclude guitar bass \
  --bpm 116 \
  --song-sticks 2 \
  --trim-start auto \
  --quality high \
  --name "Franz Ferdinand-No You Girls" \
  --out ./output
```

결과물: `output/<video_id>/final.mp3`

### 주요 옵션

| 옵션 | 설명 |
|---|---|
| `--exclude PART...` / `--include PART...` | 뺄 파트 / 남길 파트 (둘 중 하나). 기본은 `--exclude guitar bass` |
| `--bpm 116` / `--bpm auto` | BPM. 숫자를 주면 항상 우선. 기본 `auto` (아래 "BPM 자동 추정") |
| `--bpm-source mix\|drums` | BPM 추정에 쓸 오디오. 앞부분이 멜로디로 시작하면 `drums` |
| `--count-total 8` | 곡 안 스틱 카운트를 포함한 **총 카운트 수** (기본 8) |
| `--song-sticks K` | 곡 안에 이미 들어 있는 스틱 카운트 수 (기본 0). 앞에 붙는 틱 = `count-total - K` |
| `--count-in N` | 앞에 붙일 틱 개수를 직접 지정 (위 두 옵션 무시). `0`이면 카운트인 생략 |
| `--trim-start auto\|초` | 곡 앞 무음 자르기. `auto`는 첫 소리 시점을 자동 감지 |
| `--trim-offset 초` | trim-start에 더할 미세 보정값 (음수 가능) |
| `--noise-db -40` | 무음 판정 기준. 감지가 부정확하면 `-50` 등 |
| `--gain PART=dB...` | 파트별 음량 보정. 예: `--gain drums=+3`(드럼 키우기), `--gain vocals=-3`(보컬 줄이기). 키운 뒤 소리가 깨지면 `--volume`을 낮추기 |
| `--volume 0.8` | 믹스 볼륨. 소리가 깨지면(clipping) 낮추기. 클리핑 위험이 있으면 권장값을 로그로 알려 줌 |
| `--tick-freq/--tick-dur/--tick-db` | 틱 소리 (기본 1500Hz, 0.05초, -6dBFS) |
| `--name "아티스트-곡명"` | 결과물 이름. `output/<이름>/`에 `<이름>(countin+파트).mp3`와 파트별 스템 `<이름>(vocals).mp3` 등을 저장. 한 번 지정하면 작업 폴더에 기억되어 `--resume` 때 생략 가능 |
| `--quality normal\|high\|max` | 품질 프리셋 (기본 high, 아래 참고) |
| `--lossless` | `final.flac`도 함께 출력 |
| `--preview` | 앞 10초(`--preview-sec`)만 `preview.mp3`로 출력 |
| `--resume` | 이미 있는 다운로드/추출/스템/믹스를 재사용 |
| `--redo-stems` | 스템 분리를 다시 실행 (기존 스템은 `stems_backup_<시각>/`로 백업) |
| `--input-audio PATH` | 정식 음원(FLAC, mp3 320 등)을 직접 지정. 다운로드 생략 |
| `--cookies-from-browser chrome\|safari\|firefox` | yt-dlp 403/로그인 오류 시 |
| `--demucs-python PATH` | demucs가 설치된 파이썬 지정 |
| `--device cpu\|mps\|cuda` | demucs 실행 장치 (기본: demucs가 자동 선택). Apple Silicon의 `mps`는 htdemucs_6s에서 실패하므로 쓰지 마세요 |

### 카운트 개수 정하기

기본은 **총 8번**(딱딱딱딱 딱딱딱딱)입니다.

- 곡에 스틱 카운트가 없으면: 앞에 8번 → `--song-sticks 0` (기본)
- 곡 안에 스틱이 2번 들어 있으면: 앞에 6번 + 곡 안 2번 = 총 8번 → `--song-sticks 2`
- 개수를 직접 정하려면: `--count-in 4`

곡 안 스틱이 몇 번인지, 파트를 뺀 믹스에 스틱이 남아 있는지는 자동으로 판단하기 어렵습니다(스틱 뒤로 같은 간격의 소리가 이어지는 경우가 많음).
`--preview`로 들어 보고 정하세요.

### 작업 폴더

```
output/<video_id>/            # --input-audio는 output/local-<해시>/
  source.mp4                  # 다운로드 영상 (source.f*.webm 등 원본 스트림도 보존)
  song.wav                    # 추출한 오디오 (내부적으로 짧은 이름 사용)
  stems/                      # vocals/drums/bass/guitar/piano/other (+ stems.json)
  mix.wav                     # 선택 파트 믹스 (32bit float, 무손실)
  analysis.json               # 첫 소리 시점, BPM 추정 결과, 사용한 설정
  final.mp3                   # 최종 결과 (320k)
  final.flac                  # --lossless
  preview.mp3                 # --preview
```

곡마다 영상 ID로 폴더가 나뉘므로 다른 곡의 결과를 덮어쓰지 않습니다.

`--name`을 주면 이름 붙인 결과물을 따로 모아 둡니다 (카운트인이 없으면 `countin+`은 빠집니다).

```
output/Franz Ferdinand-No You Girls/
  Franz Ferdinand-No You Girls(countin+vocals+drums+piano+other).mp3
  Franz Ferdinand-No You Girls(vocals).mp3   # drums, bass, guitar, piano, other도 같은 형식
```

---

## 박 맞추기 워크플로 (`--trim-start` 미세 조정)

1. 처음 실행합니다. 스템 분리까지 한 번만 하면 됩니다.
   ```zsh
   python -m countin "URL" --bpm 116 --song-sticks 2 --preview
   ```
   로그에 `첫 소리 시점(자동 감지): 0.673초`처럼 S 값이 나옵니다.
2. `output/<id>/preview.mp3`를 들어 봅니다.
   - **곡이 카운트보다 늦게 들어옴**(틱과 첫 박 사이가 김) → 트림을 늘림: `--trim-start 0.69`
   - **곡이 카운트보다 빨리 들어옴**(첫 박이 잘리거나 당겨짐) → 트림을 줄임: `--trim-start 0.66`
   - 0.01~0.02초 단위로 조정하세요. `--trim-offset -0.01`처럼 자동 감지값에 보정값을 더해도 됩니다.
3. `--resume`을 붙이면 스템 분리를 건너뛰어 몇 초 만에 다시 확인할 수 있습니다.
   ```zsh
   python -m countin "URL" --bpm 116 --song-sticks 2 --resume --preview --trim-start 0.68
   ```
4. 맞으면 `--preview`를 빼고 실행해 `final.mp3`를 만듭니다.
   ```zsh
   python -m countin "URL" --bpm 116 --song-sticks 2 --resume --trim-start 0.68
   ```

첫 소리가 너무 일찍/늦게 잡히면 `--noise-db -50`(더 작은 소리도 소리로 인식) 또는 `-35`로 바꿔 보세요.

---

## BPM 자동 추정 (`--bpm auto`)

librosa 같은 무거운 의존성 없이, ffmpeg `silencedetect` 결과만으로 추정합니다.

1. 믹스(또는 `--bpm-source drums`면 드럼 스템)에 `silencedetect=noise=-40dB:d=0.05`를 실행해, 소리가 시작되는 시점(`silence_end`)을 모읍니다.
   첫 소리 시점 S도 같은 결과에서 구하므로 ffmpeg 분석은 한 번이면 됩니다.
2. 첫 소리부터 20초 안의 인접 간격 중 0.3~1.0초(60~200 BPM)만 후보로 씁니다.
3. 후보의 중앙값 ±15% 안에 드는 간격만 평균 → `BPM = 60 / 평균 간격`. 쉼이나 8분음표 같은 튀는 값은 제외됩니다.
4. 사용한 간격이 4개 미만이거나 표준편차가 평균의 10%를 넘으면 **"추정이 불확실합니다. --bpm 숫자를 직접 지정하세요"** 라고 출력하고 중단합니다.
5. 0.3~1.0초 간격이 부족하면 0.15~2.0초 범위로 다시 시도하고, 결과가 60~200 BPM 밖(예: 58, 232)이면 두 배/절반으로 접어 보정합니다. 보정했다는 사실은 로그에 남습니다.

소수 첫째 자리 값과 실제로 쓰는 정수 BPM이 로그에 함께 나오고, 결과는 `analysis.json`에 저장되어 같은 설정으로 다시 실행할 때 재사용됩니다.
`--bpm 116`처럼 숫자를 주면 항상 그 값을 씁니다.

---

## 음질

### 품질 프리셋 (`--quality`)

| 프리셋 | Demucs 설정 | 스템 저장 | 중간 파일 | 최종 |
|---|---|---|---|---|
| `normal` | 기본 | mp3 320 | wav | mp3 320k |
| `high` (기본) | `--shifts 2` | mp3 320 | wav | mp3 320k |
| `max` | `--shifts 4 --overlap 0.25` | FLAC (soundfile 필요, 실패 시 mp3 320 자동 폴백) | wav(24bit/float) | mp3 320k (+`--lossless`로 FLAC) |

- 손실 인코딩(mp3)은 **마지막에 한 번만** 합니다. 믹스는 32bit float wav로 저장하고, 트림·카운트인·mp3 인코딩은 한 번의 ffmpeg 호출로 처리합니다. mp3를 다시 mp3로 재인코딩하는 단계는 없습니다.
- Demucs의 wav 저장은 torchaudio 백엔드 문제(`Couldn't find appropriate backend`)가 날 수 있어, 기본값은 mp3 320 저장입니다.

### 원본 음질의 한계

유튜브 오디오는 손실 압축(AAC/Opus 약 128kbps)입니다. **최종 파일을 320k나 wav로 저장해도 원래 없던 정보는 생기지 않습니다.**
가장 큰 개선은 정식 음원을 쓰는 것입니다.

```zsh
python -m countin --input-audio ~/Music/"곡 이름 (Remastered).flac" --bpm 116 --song-sticks 2 --quality max --lossless
```

이미 만든 `final.mp3`를 320k나 wav로 다시 저장하는 "업그레이드"는 의미가 없어서 지원하지 않습니다.
품질을 바꾸려면 스템 분리부터 다시 하세요 (`--resume` 없이 실행하거나 `--resume --redo-stems`).
`--resume`인데 기존 스템의 품질 프리셋이 다르면 countin이 실행을 멈추고 알려 줍니다.

---

## 트러블슈팅

| 증상 | 해결 |
|---|---|
| `Requested format is not available` / HTTP 403 | countin은 형식 옵션(`-f`)을 쓰지 않습니다. `yt-dlp -U`로 업데이트하고, `--cookies-from-browser chrome`(또는 safari/firefox)을 시도하세요 |
| YouTube JS 챌린지/서명 관련 오류 | Deno 설치: `curl -fsSL https://deno.land/install.sh \| sh` (안내: https://github.com/yt-dlp/yt-dlp/wiki/EJS) |
| 영상이 mkv로 합쳐짐 | `--remux-video mp4`와 `--postprocessor-args "VideoRemuxer:-c:a aac"`로 mp4로 맞춥니다. 오디오는 병합 전 원본 스트림(`source.f*.webm` 등)에서 추출하므로 이 변환으로 음질이 떨어지지 않습니다 |
| `zsh: command not found: demucs` | 정상입니다. countin은 `python -m demucs`로 호출합니다. demucs가 다른 파이썬에 있으면 `--demucs-python` |
| `Couldn't find appropriate backend` | wav/flac 저장 문제. `--quality high`(mp3 320 저장)를 쓰세요. max에서는 자동 폴백됩니다 |
| Demucs가 너무 느림 / 메모리 부족 | `--quality normal`로 낮추세요 |
| `Output channels > 65536 not supported at the MPS device` | PyTorch MPS 한계입니다. `--device cpu`로 실행하세요(`--resume`을 붙이면 다운로드·추출 재사용) |
| 최종 파일 소리가 깨짐 | 로그의 "믹스 피크 레벨" 경고를 확인하고 `--volume 0.6` 등으로 낮추세요 |
| 카운트와 곡의 박이 어긋남 | 위의 "박 맞추기 워크플로" 참고. BPM 자체가 틀렸다면 `--bpm`을 직접 지정 |
| `추정이 불확실합니다` | `--bpm 숫자` 지정, 또는 `--bpm-source drums`, `--noise-db -50` |
| 한글/공백/괄호가 든 파일명 | 그대로 쓰면 됩니다(경로를 따옴표로 감싸기). 내부에서는 `song.wav` 같은 짧은 이름을 씁니다 |

## 테스트

```zsh
python3 -m unittest discover -s tests
```
