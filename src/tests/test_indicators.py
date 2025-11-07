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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])