"""BPM 추정과 카운트인 계산 단위 테스트.  실행: python3 -m unittest discover -s tests"""
import unittest

from countin.analysis import BpmUncertain, estimate_bpm, first_sound, parse_silencedetect
from countin.mix import CountIn, final_graph

# 실측: 대상 곡 첫 구간의 silence_end 시점
MEASURED = [0.673, 1.211, 1.720, 2.264, 2.758]

SILENCEDETECT_LOG = """\
[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 0.673 | silence_duration: 0.673
[silencedetect @ 0x1] silence_start: 1.1
[silencedetect @ 0x1] silence_end: 1.211 | silence_duration: 0.111
[silencedetect @ 0x1] silence_start: 1.65
[silencedetect @ 0x1] silence_end: 1.72 | silence_duration: 0.07
[silencedetect @ 0x1] silence_start: 2.2
[silencedetect @ 0x1] silence_end: 2.264 | silence_duration: 0.064
[silencedetect @ 0x1] silence_start: 2.7
[silencedetect @ 0x1] silence_end: 2.758 | silence_duration: 0.058
"""


def grid(bpm, n, start=0.673, jitter=()):
    step = 60.0 / bpm
    return [start + i * step + (jitter[i % len(jitter)] if jitter else 0.0) for i in range(n)]


class TestParse(unittest.TestCase):
    def test_parse_measured_log(self):
        onsets = parse_silencedetect(SILENCEDETECT_LOG)
        self.assertEqual(onsets, MEASURED)
        self.assertAlmostEqual(first_sound(onsets), 0.673)

    def test_sound_at_file_start(self):
        log = "silence_start: 1.0\nsilence_end: 1.5 | silence_duration: 0.5\n"
        self.assertEqual(parse_silencedetect(log), [0.0, 1.5])

    def test_no_silence_at_all(self):
        self.assertEqual(parse_silencedetect(""), [0.0])


class TestEstimate(unittest.TestCase):
    def test_measured_points(self):
        # 0.673~2.758초의 4개 간격 평균 0.52125초 → 115.1 BPM (실제 곡 116 BPM에 근접)
        est = estimate_bpm(MEASURED)
        self.assertEqual(len(est["intervals_used"]), 4)
        self.assertAlmostEqual(est["mean_interval"], 0.52125, places=4)
        self.assertAlmostEqual(est["bpm"], 115.1, places=1)
        self.assertIn(est["bpm_int"], (115, 116))

    def test_measured_points_continued(self):
        # 실측 시점 뒤로 116 BPM 박이 이어지면 116으로 수렴
        onsets = MEASURED + grid(116, 30, start=2.758 + 60 / 116)
        est = estimate_bpm(onsets)
        self.assertEqual(est["bpm_int"], 116)

    def test_outliers_excluded(self):
        # 쉼(긴 간격)과 8분음표(짧은 간격)가 섞여도 중앙값 ±15% 밖이라 제외된다
        onsets = grid(116, 12)
        onsets += [onsets[-1] + 1.5]                    # 쉼
        onsets += [onsets[-1] + 0.2586]                 # 8분음표 (0.3초 미만 → 후보 제외)
        onsets += grid(116, 6, start=onsets[-1] + 0.2586)
        est = estimate_bpm(onsets)
        self.assertEqual(est["bpm_int"], 116)
        self.assertEqual(est["notes"], [])

    def test_too_few_intervals(self):
        with self.assertRaises(BpmUncertain):
            estimate_bpm(grid(116, 4))  # 간격 3개

    def test_high_deviation(self):
        # 중앙값 ±15% 안에 있지만 편차가 커서(>10%) 불확실
        onsets = [0.0]
        for d in [0.45, 0.58, 0.45, 0.58, 0.45, 0.58]:
            onsets.append(onsets[-1] + d)
        with self.assertRaises(BpmUncertain):
            estimate_bpm(onsets)

    def test_half_time_folded(self):
        # 2분음표 위주(58 BPM 간격 1.034초) → 0.3~1.0 범위 밖 → 확장 범위 + 116으로 보정
        est = estimate_bpm(grid(58, 10))
        self.assertEqual(est["raw_bpm"], 58.0)
        self.assertEqual(est["bpm_int"], 116)
        self.assertTrue(any("보정" in n for n in est["notes"]))

    def test_double_time_folded(self):
        # 8분음표만 감지(232 BPM 간격 0.2586초) → 116으로 보정
        est = estimate_bpm(grid(232, 30))
        self.assertEqual(est["bpm_int"], 116)

    def test_window_limits_points(self):
        onsets = grid(116, 20) + grid(90, 20, start=40.0)
        est = estimate_bpm(onsets, window=20.0)
        self.assertEqual(est["bpm_int"], 116)


class TestCountIn(unittest.TestCase):
    def test_116_values(self):
        c = CountIn(count=6, bpm=116)
        self.assertAlmostEqual(c.interval, 0.51724, places=5)
        self.assertEqual(c.beat_samples, 22810)
        self.assertEqual(c.loop, 5)  # 총 틱 = loop + 1 = 6
        f = c.filter()
        self.assertIn("apad=whole_len=22810", f)
        self.assertIn("aloop=loop=5:size=22810", f)

    def test_values_follow_bpm(self):
        c = CountIn(count=8, bpm=90)
        self.assertEqual(c.beat_samples, 29400)
        self.assertIn("apad=whole_len=29400,aloop=loop=7:size=29400", c.filter())

    def test_graph_without_countin(self):
        g = final_graph(0.673, None)
        self.assertIn("atrim=start=0.6730", g)
        self.assertNotIn("concat", g)

    def test_graph_with_countin(self):
        g = final_graph(0.673, CountIn(count=6, bpm=116))
        self.assertIn("[ci][song]concat=n=2:v=0:a=1[out]", g)


if __name__ == "__main__":
    unittest.main()
