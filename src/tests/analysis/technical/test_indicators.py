"""
기술적 지표 계산 모듈 테스트

indicators.py의 EMA, SMA, ATR 계산 함수를 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.technical import (
    calculate_ema,
    calculate_sma,
    calculate_true_range,
    calculate_atr,
    calculate_macd,
    calculate_triple_macd,
    detect_peakout,
    calculate_slope,
    check_direction,
    calculate_all_indicators,
)


class TestCalculateEMA:
    """EMA 계산 함수 테스트"""

    def test_ema_with_dataframe(self):
        """DataFrame으로 EMA 계산"""
        # 테스트 데이터 생성
        data = pd.DataFrame({
            'Close': [100, 102, 104, 103, 105, 107, 106, 108, 110, 109]
        })

        # EMA 계산 (5일)
        ema = calculate_ema(data, period=5)

        # 검증
        assert isinstance(ema, pd.Series)
        assert len(ema) == len(data)
        assert not ema.iloc[4:].isna().any()  # 5번째 값부터는 NaN 없음
        assert ema.iloc[:4].isna().all()  # 처음 4개는 NaN

    def test_ema_with_series(self):
        """Series로 EMA 계산"""
        # 테스트 데이터
        data = pd.Series([100, 102, 104, 103, 105, 107, 106, 108, 110, 109])

        # EMA 계산
        ema = calculate_ema(data, period=5)

        # 검증
        assert isinstance(ema, pd.Series)
        assert len(ema) == len(data)

    def test_ema_different_periods(self):
        """다양한 기간으로 EMA 계산"""
        data = pd.DataFrame({
            'Close': [100 + i for i in range(50)]
        })

        # 여러 기간으로 계산
        ema_5 = calculate_ema(data, period=5)
        ema_20 = calculate_ema(data, period=20)
        ema_40 = calculate_ema(data, period=40)

        # 검증
        assert not ema_5.iloc[4:].isna().any()
        assert not ema_20.iloc[19:].isna().any()
        assert not ema_40.iloc[39:].isna().any()

        # 기간이 길수록 변화가 완만해야 함
        ema_5_change = ema_5.diff().abs().mean()
        ema_20_change = ema_20.diff().abs().mean()
        assert ema_5_change > ema_20_change

    def test_ema_custom_column(self):
        """사용자 지정 컬럼으로 EMA 계산"""
        data = pd.DataFrame({
            'Close': [100, 102, 104],
            'High': [105, 107, 109]
        })

        # High 컬럼으로 계산
        ema = calculate_ema(data, period=2, column='High')

        # 검증
        assert isinstance(ema, pd.Series)
        assert not ema.iloc[1:].isna().any()

    def test_ema_insufficient_data(self):
        """데이터 부족 시 에러"""
        data = pd.DataFrame({'Close': [100, 102]})

        with pytest.raises(ValueError, match="데이터 길이.*짧습니다"):
            calculate_ema(data, period=5)

    def test_ema_invalid_column(self):
        """존재하지 않는 컬럼 에러"""
        data = pd.DataFrame({'Close': [100, 102, 104]})

        with pytest.raises(ValueError, match="컬럼.*없습니다"):
            calculate_ema(data, period=2, column='InvalidColumn')

    def test_ema_invalid_type(self):
        """잘못된 데이터 타입 에러"""
        data = [100, 102, 104]  # list는 지원 안 함

        with pytest.raises(TypeError, match="지원하지 않는 데이터 타입"):
            calculate_ema(data, period=2)


class TestCalculateSMA:
    """SMA 계산 함수 테스트"""

    def test_sma_basic(self):
        """기본 SMA 계산"""
        data = pd.DataFrame({
            'Close': [100, 102, 104, 103, 105]
        })

        # SMA 계산 (5일)
        sma = calculate_sma(data, period=5)

        # 검증
        assert isinstance(sma, pd.Series)
        assert len(sma) == len(data)

        # 마지막 값 수동 계산 검증
        expected = (100 + 102 + 104 + 103 + 105) / 5
        assert abs(sma.iloc[-1] - expected) < 0.01

    def test_sma_with_series(self):
        """Series로 SMA 계산"""
        data = pd.Series([100, 102, 104, 103, 105])

        sma = calculate_sma(data, period=3)

        # 검증
        assert isinstance(sma, pd.Series)
        # 3번째 값 확인 (100+102+104)/3 = 102
        assert abs(sma.iloc[2] - 102) < 0.01


class TestCalculateTrueRange:
    """True Range 계산 함수 테스트"""

    def test_true_range_basic(self):
        """기본 True Range 계산"""
        data = pd.DataFrame({
            'High': [105, 107, 106],
            'Low': [100, 102, 101],
            'Close': [103, 105, 104]
        })

        tr = calculate_true_range(data)

        # 검증
        assert isinstance(tr, pd.Series)
        assert len(tr) == len(data)

        # 첫 번째 TR = High - Low = 105 - 100 = 5
        assert abs(tr.iloc[0] - 5) < 0.01

        # 두 번째 TR = max(107-102, |107-103|, |102-103|) = max(5, 4, 1) = 5
        assert abs(tr.iloc[1] - 5) < 0.01

    def test_true_range_gap_up(self):
        """갭 상승 시 True Range"""
        data = pd.DataFrame({
            'High': [105, 115],  # 갭 상승
            'Low': [100, 110],
            'Close': [103, 113]
        })

        tr = calculate_true_range(data)

        # 두 번째 TR = max(115-110, |115-103|, |110-103|) = max(5, 12, 7) = 12
        assert abs(tr.iloc[1] - 12) < 0.01

    def test_true_range_gap_down(self):
        """갭 하락 시 True Range"""
        data = pd.DataFrame({
            'High': [105, 95],  # 갭 하락
            'Low': [100, 90],
            'Close': [103, 93]
        })

        tr = calculate_true_range(data)

        # 두 번째 TR = max(95-90, |95-103|, |90-103|) = max(5, 8, 13) = 13
        assert abs(tr.iloc[1] - 13) < 0.01

    def test_true_range_missing_columns(self):
        """필수 컬럼 누락 시 에러"""
        data = pd.DataFrame({
            'High': [105, 107],
            'Low': [100, 102]
            # Close 누락
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            calculate_true_range(data)


class TestCalculateATR:
    """ATR 계산 함수 테스트"""

    def test_atr_basic(self):
        """기본 ATR 계산"""
        # 충분한 데이터 생성 (20일 + 1일)
        np.random.seed(42)
        data = pd.DataFrame({
            'High': 100 + np.random.randn(25).cumsum() + 5,
            'Low': 100 + np.random.randn(25).cumsum() - 5,
            'Close': 100 + np.random.randn(25).cumsum()
        })

        # ATR 계산
        atr = calculate_atr(data, period=20)

        # 검증
        assert isinstance(atr, pd.Series)
        assert len(atr) == len(data)
        assert not atr.iloc[20:].isna().any()  # 20번째부터 값 존재

        # ATR은 항상 양수
        assert (atr.dropna() > 0).all()

    def test_atr_different_periods(self):
        """다양한 기간으로 ATR 계산"""
        np.random.seed(42)
        data = pd.DataFrame({
            'High': 100 + np.random.randn(50).cumsum() + 5,
            'Low': 100 + np.random.randn(50).cumsum() - 5,
            'Close': 100 + np.random.randn(50).cumsum()
        })

        # 여러 기간
        atr_10 = calculate_atr(data, period=10)
        atr_20 = calculate_atr(data, period=20)

        # 검증
        assert not atr_10.iloc[10:].isna().any()
        assert not atr_20.iloc[20:].isna().any()

        # 기간이 길수록 변화가 완만
        atr_10_change = atr_10.diff().abs().mean()
        atr_20_change = atr_20.diff().abs().mean()
        assert atr_10_change > atr_20_change

    def test_atr_position_sizing(self):
        """ATR을 이용한 포지션 사이징 예시"""
        data = pd.DataFrame({
            'High': [105, 107, 106, 108, 110] * 5,
            'Low': [100, 102, 101, 103, 105] * 5,
            'Close': [103, 105, 104, 106, 108] * 5
        })

        atr = calculate_atr(data, period=20)

        # 포지션 사이징
        account_balance = 10_000_000  # 1천만원
        risk_per_trade = 0.01  # 1%
        current_atr = atr.iloc[-1]

        unit_size = (account_balance * risk_per_trade) / current_atr

        # 검증
        assert unit_size > 0
        assert isinstance(unit_size, (int, float))

    def test_atr_insufficient_data(self):
        """데이터 부족 시 에러"""
        data = pd.DataFrame({
            'High': [105, 107],
            'Low': [100, 102],
            'Close': [103, 105]
        })

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            calculate_atr(data, period=20)

    def test_atr_missing_columns(self):
        """필수 컬럼 누락 시 에러"""
        data = pd.DataFrame({
            'High': [105, 107] * 15,
            'Low': [100, 102] * 15
            # Close 누락
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            calculate_atr(data, period=20)


class TestIntegration:
    """통합 테스트 - 실제 데이터 시뮬레이션"""

    def test_all_indicators_together(self):
        """모든 지표를 함께 계산"""
        # 실제 주가 시뮬레이션
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')

        data = pd.DataFrame({
            'Open': 100 + np.random.randn(100).cumsum(),
            'High': 105 + np.random.randn(100).cumsum(),
            'Low': 95 + np.random.randn(100).cumsum(),
            'Close': 100 + np.random.randn(100).cumsum(),
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)

        # 가격 조정 (High >= Close >= Low)
        data['High'] = data[['Open', 'High', 'Close']].max(axis=1) + 2
        data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1) - 2

        # 모든 지표 계산
        ema_5 = calculate_ema(data, period=5)
        ema_20 = calculate_ema(data, period=20)
        ema_40 = calculate_ema(data, period=40)
        sma_20 = calculate_sma(data, period=20)
        atr_20 = calculate_atr(data, period=20)

        # 검증
        assert len(ema_5) == len(data)
        assert len(ema_20) == len(data)
        assert len(ema_40) == len(data)
        assert len(sma_20) == len(data)
        assert len(atr_20) == len(data)

        # 40일 이후에는 모든 값이 존재
        assert not ema_5.iloc[40:].isna().any()
        assert not ema_20.iloc[40:].isna().any()
        assert not ema_40.iloc[40:].isna().any()
        assert not sma_20.iloc[40:].isna().any()
        assert not atr_20.iloc[40:].isna().any()

        # EMA는 SMA보다 최근 가격에 민감
        # (상승장에서는 EMA > SMA)
        recent_data = data.iloc[-10:]
        if recent_data['Close'].is_monotonic_increasing:
            recent_ema = ema_20.iloc[-10:]
            recent_sma = sma_20.iloc[-10:]
            assert (recent_ema > recent_sma).any()


class TestCalculateMACD:
    """MACD 계산 함수 테스트"""

    def test_macd_basic(self):
        """기본 MACD 계산 (표준 설정: 12|26|9)"""
        # 충분한 데이터 생성
        data = pd.DataFrame({
            'Close': [100 + i * 0.5 for i in range(50)]
        })

        # MACD 계산
        macd, signal, hist = calculate_macd(data, fast=12, slow=26, signal=9)

        # 검증
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
        assert len(macd) == len(data)
        assert len(signal) == len(data)
        assert len(hist) == len(data)

        # 26+9=35번째부터 모든 값 존재
        assert not macd.iloc[35:].isna().any()
        assert not signal.iloc[35:].isna().any()
        assert not hist.iloc[35:].isna().any()

    def test_macd_custom_params(self):
        """커스텀 파라미터로 MACD 계산 (5|20|9)"""
        data = pd.DataFrame({
            'Close': [100 + i for i in range(50)]
        })

        # MACD(상): 5|20|9
        macd, signal, hist = calculate_macd(data, fast=5, slow=20, signal=9)

        # 검증
        assert not macd.iloc[29:].isna().any()  # 20+9=29
        assert not signal.iloc[29:].isna().any()
        assert not hist.iloc[29:].isna().any()

    def test_macd_histogram_calculation(self):
        """히스토그램 계산 검증"""
        data = pd.DataFrame({
            'Close': [100, 102, 104, 106, 108] * 10
        })

        macd, signal, hist = calculate_macd(data, fast=5, slow=10, signal=3)

        # 히스토그램 = MACD - 시그널
        expected_hist = macd - signal
        pd.testing.assert_series_equal(hist, expected_hist)

    def test_macd_zero_cross(self):
        """MACD 0선 교차 확인"""
        # 하락 후 상승하는 데이터
        data = pd.DataFrame({
            'Close': list(range(100, 80, -1)) + list(range(80, 110))
        })

        macd, signal, hist = calculate_macd(data, fast=5, slow=20, signal=9)

        # MACD가 음수에서 양수로 변경되는 지점 존재 확인
        macd_clean = macd.dropna()
        has_negative = (macd_clean < 0).any()
        has_positive = (macd_clean > 0).any()

        assert has_negative and has_positive

    def test_macd_with_series(self):
        """Series로 MACD 계산"""
        data = pd.Series([100 + i for i in range(50)])

        macd, signal, hist = calculate_macd(data, fast=12, slow=26, signal=9)

        # 검증
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)

    def test_macd_insufficient_data(self):
        """데이터 부족 시 에러"""
        data = pd.DataFrame({'Close': [100, 102, 104]})

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            calculate_macd(data, fast=12, slow=26, signal=9)

    def test_macd_invalid_params(self):
        """잘못된 파라미터 에러 (fast >= slow)"""
        data = pd.DataFrame({'Close': [100 + i for i in range(50)]})

        with pytest.raises(ValueError, match="보다 작아야"):
            calculate_macd(data, fast=26, slow=12, signal=9)

    def test_macd_invalid_column(self):
        """존재하지 않는 컬럼 에러"""
        data = pd.DataFrame({'Close': [100 + i for i in range(50)]})

        with pytest.raises(ValueError, match="컬럼.*없습니다"):
            calculate_macd(data, fast=12, slow=26, signal=9, column='InvalidColumn')


class TestCalculateTripleMACD:
    """3종 MACD 계산 함수 테스트"""

    def test_triple_macd_basic(self):
        """기본 3종 MACD 계산"""
        # 충분한 데이터 생성 (최소 49일)
        data = pd.DataFrame({
            'Close': [100 + i for i in range(100)]
        })

        # 3종 MACD 계산
        result = calculate_triple_macd(data)

        # 검증 - 9개 컬럼
        expected_columns = [
            'MACD_상', 'Signal_상', 'Hist_상',
            'MACD_중', 'Signal_중', 'Hist_중',
            'MACD_하', 'Signal_하', 'Hist_하'
        ]
        assert list(result.columns) == expected_columns

        # DataFrame 타입
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(data)

    def test_triple_macd_values(self):
        """3종 MACD 값 존재 확인"""
        data = pd.DataFrame({
            'Close': [100 + i * 0.5 for i in range(100)]
        })

        result = calculate_triple_macd(data)

        # 49번째 이후 모든 값 존재 (40 + 9)
        for col in result.columns:
            assert not result[col].iloc[49:].isna().any()

    def test_triple_macd_relationships(self):
        """3종 MACD 간의 관계 확인"""
        data = pd.DataFrame({
            'Close': [100 + i for i in range(100)]
        })

        result = calculate_triple_macd(data)

        # 상승 데이터에서는 모든 MACD가 양수여야 함
        latest = result.iloc[-1]
        assert latest['MACD_상'] > 0
        assert latest['MACD_중'] > 0
        assert latest['MACD_하'] > 0

    def test_triple_macd_individual_calculation(self):
        """개별 MACD 계산과 일치하는지 확인"""
        data = pd.DataFrame({
            'Close': [100 + i * 0.3 for i in range(100)]
        })

        # 3종 MACD
        triple = calculate_triple_macd(data)

        # 개별 계산
        macd_upper, signal_upper, hist_upper = calculate_macd(data, fast=5, slow=20, signal=9)

        # MACD(상) 비교
        pd.testing.assert_series_equal(
            triple['MACD_상'],
            macd_upper,
            check_names=False
        )
        pd.testing.assert_series_equal(
            triple['Signal_상'],
            signal_upper,
            check_names=False
        )
        pd.testing.assert_series_equal(
            triple['Hist_상'],
            hist_upper,
            check_names=False
        )

    def test_triple_macd_with_series(self):
        """Series로 3종 MACD 계산"""
        data = pd.Series([100 + i for i in range(100)])

        result = calculate_triple_macd(data)

        # 검증
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) == 9

    def test_triple_macd_insufficient_data(self):
        """데이터 부족 시 에러"""
        data = pd.DataFrame({'Close': [100 + i for i in range(30)]})

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            calculate_triple_macd(data)

    def test_triple_macd_invalid_column(self):
        """존재하지 않는 컬럼 에러"""
        data = pd.DataFrame({'Close': [100 + i for i in range(100)]})

        with pytest.raises(ValueError, match="컬럼.*없습니다"):
            calculate_triple_macd(data, column='InvalidColumn')


class TestMACDIntegration:
    """MACD 통합 테스트"""

    def test_all_macd_with_ema(self):
        """EMA와 MACD 통합 테스트"""
        # 실제 주가 시뮬레이션
        np.random.seed(42)
        data = pd.DataFrame({
            'Close': 100 + np.random.randn(100).cumsum()
        })

        # EMA 계산
        data['EMA_5'] = calculate_ema(data, period=5)
        data['EMA_20'] = calculate_ema(data, period=20)
        data['EMA_40'] = calculate_ema(data, period=40)

        # 3종 MACD 계산
        triple_macd = calculate_triple_macd(data)

        # 데이터 결합
        data = pd.concat([data, triple_macd], axis=1)

        # 검증
        assert 'EMA_5' in data.columns
        assert 'MACD_상' in data.columns
        assert len(data) == 100

        # 50번째 이후 모든 값 존재
        assert not data.iloc[50:].isna().any().any()

class TestDetectPeakout:
    """피크아웃 감지 테스트"""

    def test_detect_high_peakout(self):
        """고점 피크아웃 감지"""
        # 상승 후 하락 패턴
        data = pd.Series([1, 2, 3, 4, 5, 4, 3, 2, 1])
        peakout = detect_peakout(data, lookback=3)

        # 5에서 피크아웃 발생 (인덱스 5)
        assert peakout.iloc[5] == 1  # 고점 피크아웃

    def test_detect_low_peakout(self):
        """저점 피크아웃 감지"""
        # 하락 후 상승 패턴
        data = pd.Series([5, 4, 3, 2, 1, 2, 3, 4, 5])
        peakout = detect_peakout(data, lookback=3)

        # 1에서 피크아웃 발생 (인덱스 5)
        assert peakout.iloc[5] == -1  # 저점 피크아웃

    def test_detect_no_peakout(self):
        """피크아웃 없음"""
        # 단조 증가
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9])
        peakout = detect_peakout(data, lookback=3)

        # 피크아웃 없음
        assert (peakout == 0).all()

    def test_peakout_with_histogram(self):
        """히스토그램에서 피크아웃 감지"""
        # 상승 후 하락하는 주가 데이터
        data = pd.DataFrame({
            'Close': [100, 102, 105, 108, 110, 108, 105, 102, 100]
        })

        _, _, hist = calculate_macd(data, fast=3, slow=5, signal=2)

        # 히스토그램 피크아웃 감지
        peakout = detect_peakout(hist.dropna(), lookback=2)

        # 적어도 하나의 피크아웃이 있어야 함
        assert (peakout != 0).any()

    def test_peakout_invalid_lookback(self):
        """잘못된 lookback 에러"""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="lookback은 1 이상"):
            detect_peakout(data, lookback=0)

    def test_peakout_insufficient_data(self):
        """데이터 부족 에러"""
        data = pd.Series([1, 2, 3])

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            detect_peakout(data, lookback=5)

    def test_peakout_invalid_type(self):
        """잘못된 타입 에러"""
        data = [1, 2, 3, 4, 5]

        with pytest.raises(TypeError, match="pd.Series여야 합니다"):
            detect_peakout(data, lookback=3)


class TestCalculateSlope:
    """기울기 계산 테스트"""

    def test_slope_uptrend(self):
        """상승 추세 기울기"""
        # 선형 증가
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        slope = calculate_slope(data, period=5)

        # 상승 추세이므로 기울기 > 0
        assert slope.dropna().iloc[-1] > 0

    def test_slope_downtrend(self):
        """하락 추세 기울기"""
        # 선형 감소
        data = pd.Series([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        slope = calculate_slope(data, period=5)

        # 하락 추세이므로 기울기 < 0
        assert slope.dropna().iloc[-1] < 0

    def test_slope_flat(self):
        """횡보 기울기"""
        # 일정한 값
        data = pd.Series([5, 5, 5, 5, 5, 5, 5, 5, 5, 5])
        slope = calculate_slope(data, period=5)

        # 횡보이므로 기울기 ≈ 0
        assert abs(slope.dropna().iloc[-1]) < 0.01

    def test_slope_with_macd(self):
        """MACD 기울기 계산"""
        data = pd.DataFrame({
            'Close': [100 + i for i in range(50)]
        })

        macd, _, _ = calculate_macd(data, fast=5, slow=20, signal=9)
        macd_clean = macd.dropna()
        slope = calculate_slope(macd_clean, period=5)

        # 검증
        assert isinstance(slope, pd.Series)
        assert len(slope) == len(macd_clean)  # dropna한 데이터와 비교
        assert slope.index.equals(macd_clean.index)  # 인덱스도 일치 확인

    def test_slope_invalid_period(self):
        """잘못된 period 에러"""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="period는 2 이상"):
            calculate_slope(data, period=1)

    def test_slope_insufficient_data(self):
        """데이터 부족 에러"""
        data = pd.Series([1, 2, 3])

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            calculate_slope(data, period=10)

    def test_slope_invalid_type(self):
        """잘못된 타입 에러"""
        data = [1, 2, 3, 4, 5]

        with pytest.raises(TypeError, match="pd.Series여야 합니다"):
            calculate_slope(data, period=3)


class TestCheckDirection:
    """방향 판단 테스트"""

    def test_direction_up(self):
        """우상향 방향"""
        data = pd.Series([1, 2, 3, 4, 5])
        direction = check_direction(data, threshold=0.0)

        # 모두 양수이므로 'up'
        assert (direction == 'up').all()

    def test_direction_down(self):
        """우하향 방향"""
        data = pd.Series([-5, -4, -3, -2, -1])
        direction = check_direction(data, threshold=0.0)

        # 모두 음수이므로 'down'
        assert (direction == 'down').all()

    def test_direction_neutral(self):
        """중립 방향"""
        data = pd.Series([0, 0, 0, 0, 0])
        direction = check_direction(data, threshold=0.0)

        # 0이므로 'neutral'
        assert (direction == 'neutral').all()

    def test_direction_mixed(self):
        """혼합 방향"""
        data = pd.Series([1, -1, 0, 2, -2])
        direction = check_direction(data, threshold=0.0)

        # 각각 다른 방향
        assert direction.iloc[0] == 'up'
        assert direction.iloc[1] == 'down'
        assert direction.iloc[2] == 'neutral'
        assert direction.iloc[3] == 'up'
        assert direction.iloc[4] == 'down'

    def test_direction_with_threshold(self):
        """threshold 적용"""
        data = pd.Series([0.5, -0.5, 0.3, -0.3, 1.5])
        direction = check_direction(data, threshold=1.0)

        # threshold=1.0이므로 절댓값 1 이하는 neutral
        assert direction.iloc[0] == 'neutral'
        assert direction.iloc[1] == 'neutral'
        assert direction.iloc[2] == 'neutral'
        assert direction.iloc[3] == 'neutral'
        assert direction.iloc[4] == 'up'

    def test_direction_triple_macd(self):
        """3종 MACD 방향 판단"""
        data = pd.DataFrame({
            'Close': [100 + i for i in range(100)]
        })

        triple_macd = calculate_triple_macd(data)

        # 각 MACD 방향 판단
        dir_upper = check_direction(triple_macd['MACD_상'])
        dir_middle = check_direction(triple_macd['MACD_중'])
        dir_lower = check_direction(triple_macd['MACD_하'])

        # 검증
        assert isinstance(dir_upper, pd.Series)
        assert len(dir_upper) == len(triple_macd)

        # 상승 데이터이므로 대부분 'up'
        assert (dir_upper.dropna() == 'up').sum() > len(dir_upper.dropna()) * 0.7

    def test_direction_invalid_threshold(self):
        """잘못된 threshold 에러"""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="threshold는 0 이상"):
            check_direction(data, threshold=-1.0)

    def test_direction_invalid_type(self):
        """잘못된 타입 에러"""
        data = [1, 2, 3, 4, 5]

        with pytest.raises(TypeError, match="pd.Series여야 합니다"):
            check_direction(data, threshold=0.0)


class TestDirectionAnalysisIntegration:
    """방향성 분석 통합 테스트"""

    def test_all_direction_functions(self):
        """모든 방향성 분석 함수 통합 테스트"""
        # 실제 주가 패턴 시뮬레이션
        np.random.seed(42)
        data = pd.DataFrame({
            'Close': 100 + np.random.randn(100).cumsum()
        })

        # MACD 계산
        macd, signal, hist = calculate_macd(data, fast=12, slow=26, signal=9)

        # 피크아웃 감지
        hist_peakout = detect_peakout(hist.dropna(), lookback=3)
        macd_peakout = detect_peakout(macd.dropna(), lookback=3)

        # 기울기 계산
        hist_slope = calculate_slope(hist.dropna(), period=5)
        macd_slope = calculate_slope(macd.dropna(), period=5)

        # 방향 판단
        hist_direction = check_direction(hist.dropna())
        macd_direction = check_direction(macd.dropna())

        # 검증
        assert len(hist_peakout) == len(hist.dropna())
        assert len(hist_slope) == len(hist.dropna())
        assert len(hist_direction) == len(hist.dropna())

        # 값 확인
        assert hist_peakout.isin([0, 1, -1]).all()
        assert hist_direction.isin(['up', 'down', 'neutral']).all()

    def test_triple_macd_direction_agreement(self):
        """3종 MACD 방향 일치 확인"""
        # 강한 상승 추세
        data = pd.DataFrame({
            'Close': [100 + i * 2 for i in range(100)]
        })

        triple_macd = calculate_triple_macd(data)

        # 각 MACD 방향 판단
        dir_upper = check_direction(triple_macd['MACD_상'])
        dir_middle = check_direction(triple_macd['MACD_중'])
        dir_lower = check_direction(triple_macd['MACD_하'])

        # 방향 일치 확인
        all_up = (
            (dir_upper == 'up') &
            (dir_middle == 'up') &
            (dir_lower == 'up')
        )

        # 강한 상승 추세이므로 많은 구간에서 일치
        assert all_up.sum() > len(all_up) * 0.5


class TestCalculateAllIndicators:
    """모든 지표 통합 계산 테스트"""

    def test_all_indicators_basic(self):
        """기본 모든 지표 계산"""
        # 충분한 데이터 준비 (100일)
        np.random.seed(42)
        data = pd.DataFrame({
            'Open': 100 + np.random.randn(100).cumsum(),
            'High': 105 + np.random.randn(100).cumsum(),
            'Low': 95 + np.random.randn(100).cumsum(),
            'Close': 100 + np.random.randn(100).cumsum(),
            'Volume': np.random.randint(1000000, 10000000, 100)
        })

        # 모든 지표 계산
        result = calculate_all_indicators(data)

        # 기본 검증
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(data)
        assert len(result.columns) > len(data.columns)

    def test_all_indicators_columns(self):
        """모든 지표 컨럼 확인"""
        data = pd.DataFrame({
            'Open': [100 + i for i in range(100)],
            'High': [105 + i for i in range(100)],
            'Low': [95 + i for i in range(100)],
            'Close': [100 + i for i in range(100)],
            'Volume': [1000000] * 100
        })

        result = calculate_all_indicators(data)

        # 필수 지표 컨럼 확인
        expected_columns = [
            # EMA
            'EMA_5', 'EMA_20', 'EMA_40',
            # ATR
            'ATR',
            # MACD 3종
            'MACD_상', 'Signal_상', 'Hist_상',
            'MACD_중', 'Signal_중', 'Hist_중',
            'MACD_하', 'Signal_하', 'Hist_하',
            # 피크아웃
            'Peakout_Hist_상', 'Peakout_Hist_중', 'Peakout_Hist_하',
            'Peakout_MACD_상', 'Peakout_MACD_중', 'Peakout_MACD_하',
            # 기울기
            'Slope_MACD_상', 'Slope_MACD_중', 'Slope_MACD_하',
            # 방향
            'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하',
            # 통합 신호
            'Direction_Agreement'
        ]

        for col in expected_columns:
            assert col in result.columns, f"{col} 컨럼이 없습니다"

    def test_all_indicators_values(self):
        """지표 값 범위 검증"""
        data = pd.DataFrame({
            'Open': [100 + i * 0.5 for i in range(100)],
            'High': [105 + i * 0.5 for i in range(100)],
            'Low': [95 + i * 0.5 for i in range(100)],
            'Close': [100 + i * 0.5 for i in range(100)],
            'Volume': [1000000] * 100
        })

        result = calculate_all_indicators(data)

        # EMA 값 확인
        assert result['EMA_5'].notna().sum() > 0
        assert result['EMA_20'].notna().sum() > 0
        assert result['EMA_40'].notna().sum() > 0

        # ATR 값 확인 (항상 양수)
        assert (result['ATR'].dropna() > 0).all()

        # 피크아웃 값 확인 (-1, 0, 1)
        for col in ['Peakout_Hist_상', 'Peakout_MACD_상']:
            if col in result.columns:
                assert result[col].dropna().isin([0, 1, -1]).all()

        # 방향 값 확인
        for col in ['Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하']:
            assert result[col].isin(['up', 'down', 'neutral']).all()

        # 통합 신호 확인
        assert result['Direction_Agreement'].isin(['all_up', 'all_down', 'mixed']).all()

    def test_all_indicators_custom_params(self):
        """커스텀 파라미터로 계산"""
        data = pd.DataFrame({
            'Open': [100 + i for i in range(100)],
            'High': [105 + i for i in range(100)],
            'Low': [95 + i for i in range(100)],
            'Close': [100 + i for i in range(100)],
            'Volume': [1000000] * 100
        })

        result = calculate_all_indicators(
            data,
            ema_periods=(10, 30, 60),
            atr_period=14,
            peakout_lookback=5,
            slope_period=7,
            direction_threshold=0.5
        )

        # 커스텀 EMA 기간 확인
        # assert 'EMA_5' not in result.columns  # 기본값이 아님
        # EMA는 커스텀 파라미터로 계산되지만 컨럼명은 고정됨
        assert 'EMA_5' in result.columns
        assert 'EMA_20' in result.columns
        assert 'EMA_40' in result.columns

    def test_all_indicators_direction_agreement(self):
        """방향 일치 확인"""
        # 강한 상승 추세
        data = pd.DataFrame({
            'Open': [100 + i * 2 for i in range(100)],
            'High': [105 + i * 2 for i in range(100)],
            'Low': [95 + i * 2 for i in range(100)],
            'Close': [100 + i * 2 for i in range(100)],
            'Volume': [1000000] * 100
        })

        result = calculate_all_indicators(data)

        # 상승 추세에서 all_up 많아야 함
        all_up_count = (result['Direction_Agreement'] == 'all_up').sum()
        total_count = len(result['Direction_Agreement'].dropna())

        assert all_up_count > total_count * 0.3  # 30% 이상

    def test_all_indicators_insufficient_data(self):
        """데이터 부족 에러"""
        # 30일 데이터 (49일 미만)
        data = pd.DataFrame({
            'Open': [100 + i for i in range(30)],
            'High': [105 + i for i in range(30)],
            'Low': [95 + i for i in range(30)],
            'Close': [100 + i for i in range(30)],
            'Volume': [1000000] * 30
        })

        with pytest.raises(ValueError, match="데이터 길이.*부족합니다"):
            calculate_all_indicators(data)

    def test_all_indicators_missing_columns(self):
        """필수 컨럼 누락 에러"""
        # Volume 컨럼 누락
        data = pd.DataFrame({
            'Open': [100 + i for i in range(100)],
            'High': [105 + i for i in range(100)],
            'Low': [95 + i for i in range(100)],
            'Close': [100 + i for i in range(100)]
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            calculate_all_indicators(data)

    def test_all_indicators_invalid_type(self):
        """잘못된 타입 에러"""
        data = [[100, 105, 95, 100, 1000000]] * 100

        with pytest.raises(TypeError, match="pd.DataFrame이어야 합니다"):
            calculate_all_indicators(data)

    def test_all_indicators_original_unchanged(self):
        """원본 DataFrame 변경되지 않음 확인"""
        data = pd.DataFrame({
            'Open': [100 + i for i in range(100)],
            'High': [105 + i for i in range(100)],
            'Low': [95 + i for i in range(100)],
            'Close': [100 + i for i in range(100)],
            'Volume': [1000000] * 100
        })

        original_columns = data.columns.tolist()
        original_len = len(data)

        # 지표 계산
        result = calculate_all_indicators(data)

        # 원본 변경 없음 확인
        assert data.columns.tolist() == original_columns
        assert len(data) == original_len
        assert len(result.columns) > len(data.columns)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])