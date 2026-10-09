# O.O.O – 사랑이란 선 하나 긋고서 · HeadRush Flex Prime 톤 가이드

- 장비: HeadRush Flex Prime (매뉴얼 v5.2.0 기준)
- 근거: countin으로 분리한 기타 트랙 `(guitar).flac`을 측정한 결과 + Flex Prime 매뉴얼과 공식 모델 목록
- 주의: 직접 들어보고 만든 세팅이 아니라 측정값으로 만든 세팅입니다. 아래 값은 출발점으로 쓰고, 실제로 들으면서 맞춰 주세요.

---

## 1. 기타 트랙을 측정해서 알게 된 것

| 측정 결과 | 의미 | 세팅에 반영한 것 |
|---|---|---|
| 왼쪽과 오른쪽 소리가 거의 겹치지 않음 (상관 0.09) | 기타 두 대를 따로 녹음해서 좌우로 나눈 더블트래킹 | 앰프를 X2 Stereo-Doubling으로 설정 |
| 4kHz 위가 급하게 줄어듦 (6kHz 위는 거의 없음) | 쏘지 않고 따뜻한 톤 | High Cut을 약 5.5kHz로 |
| 120~250Hz가 가장 큼 | 몸통이 두꺼운 톤 | Bass를 너무 깎지 않기 |
| 크레스트 약 14dB, 음이 길게 유지됨 | 하이게인이 아니고 크런치에 컴프가 걸린 정도 | 게인은 중간, 컴프는 약하게 |
| BPM 약 190, 코드 중심은 D·A·G | 딜레이 시간 계산에 사용 | 템포를 190으로 고정 |

### 시간대별 변화 (측정값으로 추정한 것이니 들으면서 확인)

| 구간 | 특징 |
|---|---|
| 0~10초 인트로 / 170초~ 아웃트로 | 밝은 편 |
| 10~30초, 70~80초 (벌스) | 어둡고 부드러움 |
| 30~110초 | 중간 밝기 |
| 115~140초 | 곡 전체에서 가장 크고(+5dB) 가장 밝음 → 클라이맥스 후렴 |
| 145~165초 | 아주 어둡고 소리가 가운데로 모임 → 브릿지 |

이 흐름에 맞춰 **한 리그 안에 씬 3개(벌스 / 후렴 / 브릿지)**를 만듭니다.

---

## 2. 리그 구성 (Straight Path)

| 슬롯 | 블록 | 설정 |
|---|---|---|
| Input | 리그 입력 설정 | Gate Thrsh 약 −60dB, Noise Filt 약 −90dB |
| 1 | **Gray Comp** (Compressor) | Sustain 30~40%, Level은 켰다 껐다 할 때 볼륨이 같아지는 지점. Advanced 페이지(슬라이더 아이콘) Block Mix 50~70% |
| 2 | **Jimmy OD** (Drive) — 후렴에서만 켬 | Gain 20~30%, Level 60~70%. Tone 노브가 없으므로 음색은 Advanced 페이지 EQ로(High Mid/High 밴드). 앰프를 더 밀어주는 용도 |
| 3 | **64 Black Lux Norm** (Fender Deluxe Reverb), X2 Stereo-Doubling | 아래 "앰프 노브" 참고 |
| 4 | **1X12 Black Panel Lux** cab | 다이내믹 마이크, On-Axis |
| 5 | (블록 없이) **캡 블록 Advanced 페이지 EQ** | EQ On. Low(왼쪽 1번 점) Mode=Cut, 80Hz / High(4번 점) Mode=Cut, 5,500Hz / High Mid(3번 점) 2,500~3,000Hz −2dB (매뉴얼 p26~27) |
| 6 | **Tape Echo** 또는 **BBD Delay** | 4분음표 = **316ms** (190BPM), Mix 10~12%, Feedback 15~20% |
| 7 | **Spring Reverb** 또는 **AIR Reverb** (Room) | Mix 15~18% |

### 앰프 노브 (화면 표시는 %, 모델마다 노브 구성이 조금 다름)

- Volume/Drive 50~60%: 세게 치면 살짝 깨지고 약하게 치면 맑아지는 지점
- Bass 50%, Treble 50%
- 64 Black Lux Norm(Deluxe Reverb)은 원래 앰프처럼 **Mid 노브가 없음**. 합주에서 기타가 묻히면 앰프 블록 Advanced 페이지 EQ의 Low Mid(왼쪽 2번 점) 밴드를 800Hz 부근 +2dB
- Master 노브가 없는 모델이면 무시하고, 전체 볼륨은 Advanced 페이지 Output Gain으로

> 이펙트별 노브 이름과 범위는 매뉴얼에 나와 있지 않습니다. 화면에 다른 노브가 보이면 이름에 맞춰 조정하세요.

### 스테레오 더블링

- 앰프 블록을 탭 → 오른쪽 위 **X2** → **Stereo-Doubling** 선택 (매뉴얼 4.1.4)
- 아래쪽 앰프는 **66 AC Hi Boost** (Vox AC30)로 바꾸기 → 원곡처럼 좌우 질감이 달라짐
- 폭 조절: Out 아이콘 더블탭 → **Rig Width** (매뉴얼 4.3.3)

> **합주할 때**: 밴드에 기타가 두 명이면 원곡에서도 L/R을 한 파트씩 나눠 맡았을 가능성이 높습니다. 이럴 때는 X2를 끄고 모노로 쓰는 게 덜 뭉칩니다. 하나의 PA 채널에 모노로 들어갈 때도 마찬가지입니다.

### 바꿔 볼 만한 앰프

- 톤이 너무 둥글면 → **66 AC Hi Boost**를 메인 앰프로
- 더 거칠게 가고 싶으면 → **05 Tangerine 30 Ch2** (Orange)

---

## 3. 씬 설정 (매뉴얼 4.6.2)

메뉴 → Hardware Assign → 각 풋스위치를 **Scene**으로 바꾸고 → Edit

| 풋스위치 | 씬 | Jimmy OD | Delay | Reverb | 그 밖의 설정 |
|---|---|---|---|---|---|
| FS1 | **벌스** | Off | On | On | 기본 상태 |
| FS2 | **후렴/클라이맥스** | **On** | On | On | 115~140초 구간의 밝고 큰 톤 |
| FS3 | **브릿지** | Off | Off | On | 리버브 블록 프리셋을 Mix 30%로 저장해 두고 씬에서 불러오기. 기타는 넥 픽업 + 톤 노브 줄이기 |

- 같은 화면 위쪽 **Tempo** → **Fixed 190 BPM** (딜레이를 곡 템포에 맞춤)
- FS3 길게 누르기(기본은 튜너)를 **Bank A/B**로 바꾸면 스위치를 6개까지 사용 가능 (매뉴얼 4.6.1)
- 다 했으면 **리그 저장**. Hardware Assign 설정도 리그와 함께 저장됩니다.

---

## 4. 원곡 기타와 비교하며 맞추기

Flex Prime의 **Practice Tool** (매뉴얼 4.14)로 countin `output/` 폴더의 트랙을 바로 재생할 수 있습니다.

1. USB Transfer로 `(guitar).flac`과 `(countin+vocals+drums+piano+other).mp3`를 Flex Prime에 옮깁니다. flac이 목록에 안 보이면 mp3로 변환해서 넣으세요.
2. **guitar 트랙**은 115~140초 구간을 Loop으로 걸어 놓고 내 톤과 번갈아 들으며 맞춥니다.
3. 톤이 맞으면 **기타를 뺀 트랙**을 틀고 같이 쳐 보면서 확인합니다.

### 비교하며 조정하는 기준

| 내 톤이… | 이렇게 |
|---|---|
| 원곡보다 쏨 | High Cut을 5kHz까지 내리기 |
| 원곡보다 얇음 | 앰프 Bass 올리기, 또는 EQ로 200Hz 부근 +2dB |
| 원곡보다 더 깨짐 | 기타 볼륨을 8 정도로 줄이기 |

---

## 출처

- [HeadRush Flex Prime 제품 페이지 및 모델 목록](https://headrushfx.com/products/flex-prime/index.html)
- [Flex Prime 사용자 가이드 v5.2.0 (PDF)](https://cdn.inmusicbrands.com/Software/SGEE/52/HeadRush%20Flex%20Prime%20-%20User%20Guide%20-%20v5.2.0.pdf)
- [Flex Prime FAQ](https://support.headrushfx.com/en/support/solutions/articles/69000862402-headrush-flex-prime-frequently-asked-questions)
- O.O.O 밴드 정보: [텐아시아](https://www.tenasia.co.kr/article/2016012509904), [헤럴드경제](https://www.heraldk.com/article/2014060123312615612)
