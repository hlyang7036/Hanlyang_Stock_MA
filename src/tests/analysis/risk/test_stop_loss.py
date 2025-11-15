"""
손절 관리 모듈 테스트

테스트 대상:
- calculate_volatility_stop: 변동성 기반 손절가 계산
- calculate_trend_stop: 추세 기반 손절가 계산
- get_stop_loss_price: 최종 손절가 결정
- check_stop_loss_triggered: 손절 발동 체크
- update_trailing_stop: 트레일링 스톱 업데이트
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.risk.stop_loss import (
    calculate_volatility_stop,
    calculate_trend_stop,
    get_stop_loss_price,
    check_stop_loss_triggered,
    update_trailing_stop
)


class TestCalculateVolatilityStop:
    """변동성 기반 손절가 계산 테스트"""
    
    def test_long_position_standard(self):
        """매수 포지션 표준 케이스"""
        result = calculate_volatility_stop(50_000, 1_000, 'long', 2.0)
        
        assert result == 48_000.0
    
    def test_short_position_standard(self):
        """매도 포지션 표준 케이스"""
        result = calculate_volatility_stop(50_000, 1_000, 'short', 2.0)
        
        assert result == 52_000.0
    
    def test_tight_stop_1_5_multiplier(self):
        """타이트한 손절 (1.5배)"""
        result = calculate_volatility_stop(50_000, 1_000, 'long', 1.5)
        
        assert result == 48_500.0
    
    def test_loose_stop_3_0_multiplier(self):
        """여유로운 손절 (3.0배)"""
        result = calculate_volatility_stop(50_000, 1_000, 'long', 3.0)
        
        assert result == 47_000.0
    
    def test_high_volatility_wider_stop(self):
        """고변동성 → 넓은 손절폭"""
        result = calculate_volatility_stop(50_000, 2_000, 'long', 2.0)
        
        assert result == 46_000.0
    
    def test_low_volatility_tighter_stop(self):
        """저변동성 → 좁은 손절폭"""
        result = calculate_volatility_stop(50_000, 500, 'long', 2.0)
        
        assert result == 49_000.0
    
    def test_expensive_stock(self):
        """고가 주식"""
        result = calculate_volatility_stop(1_000_000, 10_000, 'long', 2.0)
        
        assert result == 980_000.0
    
    def test_cheap_stock(self):
        """저가 주식"""
        result = calculate_volatility_stop(10_000, 500, 'long', 2.0)
        
        assert result == 9_000.0
    
    def test_negative_stop_prevented(self):
        """음수 손절가 방지"""
        # 진입가 1,000원, ATR 1,000원 → 손절가 -1,000원 → 0원
        result = calculate_volatility_stop(1_000, 1_000, 'long', 2.0)
        
        assert result == 0.0
    
    def test_case_insensitive_position_type(self):
        """대소문자 구분 없음"""
        result_upper = calculate_volatility_stop(50_000, 1_000, 'LONG', 2.0)
        result_lower = calculate_volatility_stop(50_000, 1_000, 'long', 2.0)
        result_mixed = calculate_volatility_stop(50_000, 1_000, 'Long', 2.0)
        
        assert result_upper == result_lower == result_mixed
    
    def test_zero_entry_price_raises_error(self):
        """진입가 0 → ValueError"""
        with pytest.raises(ValueError, match="진입가는 양수여야"):
            calculate_volatility_stop(0, 1_000, 'long', 2.0)
    
    def test_negative_entry_price_raises_error(self):
        """진입가 음수 → ValueError"""
        with pytest.raises(ValueError, match="진입가는 양수여야"):
            calculate_volatility_stop(-50_000, 1_000, 'long', 2.0)
    
    def test_zero_atr_raises_error(self):
        """ATR 0 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            calculate_volatility_stop(50_000, 0, 'long', 2.0)
    
    def test_negative_atr_raises_error(self):
        """ATR 음수 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            calculate_volatility_stop(50_000, -1_000, 'long', 2.0)
    
    def test_invalid_position_type_raises_error(self):
        """잘못된 position_type → ValueError"""
        with pytest.raises(ValueError, match="'long' 또는 'short'여야"):
            calculate_volatility_stop(50_000, 1_000, 'buy', 2.0)
    
    def test_zero_multiplier_raises_error(self):
        """multiplier 0 → ValueError"""
        with pytest.raises(ValueError, match="atr_multiplier는 양수여야"):
            calculate_volatility_stop(50_000, 1_000, 'long', 0)
    
    def test_negative_multiplier_raises_error(self):
        """multiplier 음수 → ValueError"""
        with pytest.raises(ValueError, match="atr_multiplier는 양수여야"):
            calculate_volatility_stop(50_000, 1_000, 'long', -2.0)
    
    def test_invalid_entry_price_type_raises_error(self):
        """잘못된 entry_price 타입 → TypeError"""
        with pytest.raises(TypeError, match="entry_price는 숫자여야"):
            calculate_volatility_stop("50000", 1_000, 'long', 2.0)
    
    def test_invalid_atr_type_raises_error(self):
        """잘못된 ATR 타입 → TypeError"""
        with pytest.raises(TypeError, match="atr은 숫자여야"):
            calculate_volatility_stop(50_000, "1000", 'long', 2.0)
    
    def test_invalid_position_type_type_raises_error(self):
        """잘못된 position_type 타입 → TypeError"""
        with pytest.raises(TypeError, match="position_type은 문자열이어야"):
            calculate_volatility_stop(50_000, 1_000, 123, 2.0)
    
    def test_float_inputs_work(self):
        """실수 입력 → 정상 작동"""
        result = calculate_volatility_stop(50_000.0, 1_000.0, 'long', 2.0)
        
        assert result == 48_000.0


class TestCalculateTrendStop:
    """추세 기반 손절가 계산 테스트"""
    
    def test_long_position_uses_ma(self):
        """매수 포지션 → 이동평균선 사용"""
        data = pd.DataFrame({
            'EMA_20': [49_000, 49_500, 50_000, 50_500, 51_000]
        })
        
        result = calculate_trend_stop(data, 'long', 'EMA_20')
        
        assert len(result) == 5
        assert result.iloc[0] == 49_000
        assert result.iloc[-1] == 51_000
    
    def test_short_position_uses_ma(self):
        """매도 포지션 → 이동평균선 사용"""
        data = pd.DataFrame({
            'EMA_20': [51_000, 50_500, 50_000, 49_500, 49_000]
        })
        
        result = calculate_trend_stop(data, 'short', 'EMA_20')
        
        assert len(result) == 5
        assert result.iloc[0] == 51_000
        assert result.iloc[-1] == 49_000
    
    def test_different_ma_columns(self):
        """다른 이동평균선 사용"""
        data = pd.DataFrame({
            'EMA_20': [49_000, 49_500, 50_000],
            'EMA_40': [48_000, 48_500, 49_000],
            'EMA_60': [47_000, 47_500, 48_000]
        })
        
        result_20 = calculate_trend_stop(data, 'long', 'EMA_20')
        result_40 = calculate_trend_stop(data, 'long', 'EMA_40')
        result_60 = calculate_trend_stop(data, 'long', 'EMA_60')
        
        assert result_20.iloc[0] > result_40.iloc[0] > result_60.iloc[0]
    
    def test_case_insensitive_position_type(self):
        """대소문자 구분 없음"""
        data = pd.DataFrame({
            'EMA_20': [50_000, 51_000, 52_000]
        })
        
        result_upper = calculate_trend_stop(data, 'LONG', 'EMA_20')
        result_lower = calculate_trend_stop(data, 'long', 'EMA_20')
        
        assert all(result_upper == result_lower)
    
    def test_missing_ma_column_raises_error(self):
        """필수 컬럼 누락 → ValueError"""
        data = pd.DataFrame({
            'Close': [50_000, 51_000, 52_000]
        })
        
        with pytest.raises(ValueError, match="EMA_20 컬럼이 필요합니다"):
            calculate_trend_stop(data, 'long', 'EMA_20')
    
    def test_invalid_position_type_raises_error(self):
        """잘못된 position_type → ValueError"""
        data = pd.DataFrame({
            'EMA_20': [50_000, 51_000, 52_000]
        })
        
        with pytest.raises(ValueError, match="'long' 또는 'short'여야"):
            calculate_trend_stop(data, 'buy', 'EMA_20')
    
    def test_invalid_data_type_raises_error(self):
        """잘못된 data 타입 → TypeError"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            calculate_trend_stop([1, 2, 3], 'long', 'EMA_20')
    
    def test_invalid_position_type_type_raises_error(self):
        """잘못된 position_type 타입 → TypeError"""
        data = pd.DataFrame({
            'EMA_20': [50_000, 51_000, 52_000]
        })
        
        with pytest.raises(TypeError, match="position_type은 문자열이어야"):
            calculate_trend_stop(data, 123, 'EMA_20')
    
    def test_returns_series(self):
        """pd.Series 반환"""
        data = pd.DataFrame({
            'EMA_20': [50_000, 51_000, 52_000]
        })
        
        result = calculate_trend_stop(data, 'long', 'EMA_20')
        
        assert isinstance(result, pd.Series)


class TestGetStopLossPrice:
    """최종 손절가 결정 테스트"""
    
    def test_long_uses_higher_stop(self):
        """매수 포지션 → 더 높은 손절가 선택"""
        # 변동성: 48,000 / 추세: 49,000 → 49,000 선택
        result = get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'long')
        
        assert result['stop_price'] == 49_000.0
        assert result['stop_type'] == 'trend'
    
    def test_short_uses_lower_stop(self):
        """매도 포지션 → 더 낮은 손절가 선택"""
        # 변동성: 52,000 / 추세: 51,000 → 51,000 선택
        result = get_stop_loss_price(50_000, 48_000, 1_000, 51_000, 'short')
        
        assert result['stop_price'] == 51_000.0
        assert result['stop_type'] == 'trend'
    
    def test_returns_all_required_keys(self):
        """모든 필수 키 반환"""
        result = get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'long')
        
        required_keys = [
            'stop_price', 'stop_type', 'distance', 'distance_won',
            'risk_amount', 'volatility_stop', 'trend_stop'
        ]
        
        for key in required_keys:
            assert key in result
    
    def test_distance_calculation(self):
        """거리 계산"""
        result = get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'long')
        
        # 현재가 52,000 - 손절가 49,000 = 3,000원
        assert result['distance_won'] == 3_000.0
        # 3,000 / 52,000 = 5.77%
        assert abs(result['distance'] - 0.0577) < 0.001
    
    def test_risk_amount_calculation(self):
        """리스크 금액 계산"""
        result = get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'long')
        
        # 진입가 50,000 - 손절가 49,000 = 1,000원
        assert result['risk_amount'] == 1_000.0
    
    def test_volatility_stop_preferred(self):
        """변동성 손절가 선택"""
        # 변동성: 48,000 / 추세: 47,000 → 48,000 선택 (매수)
        result = get_stop_loss_price(50_000, 52_000, 1_000, 47_000, 'long')
        
        assert result['stop_price'] == 48_000.0
        assert result['stop_type'] == 'volatility'
    
    def test_includes_both_stops(self):
        """두 손절가 모두 포함"""
        result = get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'long')
        
        assert result['volatility_stop'] == 48_000.0
        assert result['trend_stop'] == 49_000.0
    
    def test_zero_entry_price_raises_error(self):
        """진입가 0 → ValueError"""
        with pytest.raises(ValueError, match="진입가는 양수여야"):
            get_stop_loss_price(0, 52_000, 1_000, 49_000, 'long')
    
    def test_zero_current_price_raises_error(self):
        """현재가 0 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            get_stop_loss_price(50_000, 0, 1_000, 49_000, 'long')
    
    def test_zero_atr_raises_error(self):
        """ATR 0 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            get_stop_loss_price(50_000, 52_000, 0, 49_000, 'long')
    
    def test_zero_trend_stop_raises_error(self):
        """추세 손절가 0 → ValueError"""
        with pytest.raises(ValueError, match="추세 손절가는 양수여야"):
            get_stop_loss_price(50_000, 52_000, 1_000, 0, 'long')
    
    def test_invalid_position_type_raises_error(self):
        """잘못된 position_type → ValueError"""
        with pytest.raises(ValueError, match="'long' 또는 'short'여야"):
            get_stop_loss_price(50_000, 52_000, 1_000, 49_000, 'buy')


class TestCheckStopLossTriggered:
    """손절 발동 체크 테스트"""
    
    def test_long_position_triggered(self):
        """매수 포지션 손절 발동"""
        # 현재가 47,000 <= 손절가 48,000 → 손절
        result = check_stop_loss_triggered(47_000, 48_000, 'long')
        
        assert result is True
    
    def test_long_position_not_triggered(self):
        """매수 포지션 정상"""
        # 현재가 49,000 > 손절가 48,000 → 정상
        result = check_stop_loss_triggered(49_000, 48_000, 'long')
        
        assert result is False
    
    def test_long_position_exact_stop(self):
        """매수 포지션 정확히 손절가"""
        # 현재가 48,000 == 손절가 48,000 → 손절
        result = check_stop_loss_triggered(48_000, 48_000, 'long')
        
        assert result is True
    
    def test_short_position_triggered(self):
        """매도 포지션 손절 발동"""
        # 현재가 53,000 >= 손절가 52,000 → 손절
        result = check_stop_loss_triggered(53_000, 52_000, 'short')
        
        assert result is True
    
    def test_short_position_not_triggered(self):
        """매도 포지션 정상"""
        # 현재가 51,000 < 손절가 52,000 → 정상
        result = check_stop_loss_triggered(51_000, 52_000, 'short')
        
        assert result is False
    
    def test_short_position_exact_stop(self):
        """매도 포지션 정확히 손절가"""
        # 현재가 52,000 == 손절가 52,000 → 손절
        result = check_stop_loss_triggered(52_000, 52_000, 'short')
        
        assert result is True
    
    def test_case_insensitive_position_type(self):
        """대소문자 구분 없음"""
        result_upper = check_stop_loss_triggered(47_000, 48_000, 'LONG')
        result_lower = check_stop_loss_triggered(47_000, 48_000, 'long')
        
        assert result_upper == result_lower
    
    def test_zero_current_price_raises_error(self):
        """현재가 0 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            check_stop_loss_triggered(0, 48_000, 'long')
    
    def test_zero_stop_price_raises_error(self):
        """손절가 0 → ValueError"""
        with pytest.raises(ValueError, match="손절가는 양수여야"):
            check_stop_loss_triggered(47_000, 0, 'long')
    
    def test_invalid_position_type_raises_error(self):
        """잘못된 position_type → ValueError"""
        with pytest.raises(ValueError, match="'long' 또는 'short'여야"):
            check_stop_loss_triggered(47_000, 48_000, 'buy')
    
    def test_invalid_current_price_type_raises_error(self):
        """잘못된 current_price 타입 → TypeError"""
        with pytest.raises(TypeError, match="current_price는 숫자여야"):
            check_stop_loss_triggered("47000", 48_000, 'long')
    
    def test_returns_boolean(self):
        """boolean 반환"""
        result = check_stop_loss_triggered(47_000, 48_000, 'long')
        
        assert isinstance(result, bool)


class TestUpdateTrailingStop:
    """트레일링 스톱 업데이트 테스트"""
    
    def test_long_new_high_updates_stop(self):
        """매수 포지션 신고가 → 손절가 상향"""
        # 최고가 55,000 - 2,000 = 53,000
        result = update_trailing_stop(50_000, 55_000, 48_000, 1_000, 'long')
        
        assert result == 53_000.0
    
    def test_long_no_new_high_keeps_stop(self):
        """매수 포지션 신고가 아님 → 손절가 유지"""
        # 최고가 52,000 - 2,000 = 50,000 < 현재 손절가 51,000
        result = update_trailing_stop(50_000, 52_000, 51_000, 1_000, 'long')
        
        assert result == 51_000.0
    
    def test_long_min_at_entry_price(self):
        """매수 포지션 최소 진입가"""
        # 최고가 51,000 - 2,000 = 49,000 < 진입가 50,000 → 50,000
        result = update_trailing_stop(50_000, 51_000, 48_000, 1_000, 'long')
        
        assert result == 50_000.0
    
    def test_short_new_low_updates_stop(self):
        """매도 포지션 신저가 → 손절가 하향"""
        # 최저가 45,000 + 2,000 = 47,000
        result = update_trailing_stop(50_000, 45_000, 52_000, 1_000, 'short')
        
        assert result == 47_000.0
    
    def test_short_no_new_low_keeps_stop(self):
        """매도 포지션 신저가 아님 → 손절가 유지"""
        # 최저가 48,000 + 2,000 = 50,000 > 현재 손절가 49,000
        result = update_trailing_stop(50_000, 48_000, 49_000, 1_000, 'short')
        
        assert result == 49_000.0
    
    def test_short_max_at_entry_price(self):
        """매도 포지션 최대 진입가"""
        # 최저가 49,000 + 2,000 = 51,000 > 진입가 50,000 → 50,000
        result = update_trailing_stop(50_000, 49_000, 52_000, 1_000, 'short')
        
        assert result == 50_000.0
    
    def test_long_tight_trailing(self):
        """매수 포지션 타이트한 트레일링 (1.5배)"""
        # 최고가 55,000 - 1,500 = 53,500
        result = update_trailing_stop(50_000, 55_000, 48_000, 1_000, 'long', 1.5)
        
        assert result == 53_500.0
    
    def test_long_loose_trailing(self):
        """매수 포지션 여유로운 트레일링 (3.0배)"""
        # 최고가 55,000 - 3,000 = 52,000
        result = update_trailing_stop(50_000, 55_000, 48_000, 1_000, 'long', 3.0)
        
        assert result == 52_000.0
    
    def test_zero_entry_price_raises_error(self):
        """진입가 0 → ValueError"""
        with pytest.raises(ValueError, match="진입가는 양수여야"):
            update_trailing_stop(0, 55_000, 48_000, 1_000, 'long')
    
    def test_zero_highest_price_raises_error(self):
        """최고가/최저가 0 → ValueError"""
        with pytest.raises(ValueError, match="최고가/최저가는 양수여야"):
            update_trailing_stop(50_000, 0, 48_000, 1_000, 'long')
    
    def test_zero_current_stop_raises_error(self):
        """현재 손절가 0 → ValueError"""
        with pytest.raises(ValueError, match="현재 손절가는 양수여야"):
            update_trailing_stop(50_000, 55_000, 0, 1_000, 'long')
    
    def test_zero_atr_raises_error(self):
        """ATR 0 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            update_trailing_stop(50_000, 55_000, 48_000, 0, 'long')
    
    def test_invalid_position_type_raises_error(self):
        """잘못된 position_type → ValueError"""
        with pytest.raises(ValueError, match="'long' 또는 'short'여야"):
            update_trailing_stop(50_000, 55_000, 48_000, 1_000, 'buy')
    
    def test_returns_float(self):
        """float 반환"""
        result = update_trailing_stop(50_000, 55_000, 48_000, 1_000, 'long')
        
        assert isinstance(result, float)


class TestIntegration:
    """통합 테스트"""
    
    def test_complete_stop_loss_workflow(self):
        """전체 손절 관리 워크플로우"""
        # 1. 초기 진입
        entry_price = 50_000
        current_price = 50_000
        atr = 1_000
        
        # 2. 데이터프레임 생성
        data = pd.DataFrame({
            'EMA_20': [45_000, 46_000, 47_000, 48_000, 49_000]
        })
        
        # 3. 추세 손절가 계산
        trend_stops = calculate_trend_stop(data, 'long', 'EMA_20')
        trend_stop = trend_stops.iloc[-1]  # 최신값
        
        # 4. 최종 손절가 결정
        stop_info = get_stop_loss_price(
            entry_price, current_price, atr, trend_stop, 'long'
        )
        
        assert 'stop_price' in stop_info
        assert stop_info['stop_price'] > 0
        
        # 5. 손절 체크 (정상)
        triggered = check_stop_loss_triggered(
            current_price, stop_info['stop_price'], 'long'
        )
        assert triggered is False
        
        # 6. 트레일링 스톱 (신고가)
        new_high = 55_000
        new_stop = update_trailing_stop(
            entry_price, new_high, stop_info['stop_price'], atr, 'long'
        )
        
        assert new_stop > stop_info['stop_price']
    
    def test_stop_loss_prevents_large_loss(self):
        """손절이 큰 손실 방지"""
        entry_price = 50_000
        atr = 1_000
        
        # 변동성 손절가
        vol_stop = calculate_volatility_stop(entry_price, atr, 'long', 2.0)
        
        # 최대 손실 = 2 ATR
        max_loss = entry_price - vol_stop
        assert max_loss == 2_000
        
        # 손실률 = 4%
        loss_pct = max_loss / entry_price
        assert abs(loss_pct - 0.04) < 0.001
    
    def test_trailing_stop_protects_profit(self):
        """트레일링 스톱이 수익 보호"""
        entry_price = 50_000
        initial_stop = 48_000
        atr = 1_000
        
        # 수익 발생
        new_high = 60_000
        
        # 트레일링 업데이트
        new_stop = update_trailing_stop(
            entry_price, new_high, initial_stop, atr, 'long'
        )
        
        # 새 손절가 = 60,000 - 2,000 = 58,000
        assert new_stop == 58_000.0
        
        # 최소 수익 보장 = 8,000원 (16%)
        guaranteed_profit = new_stop - entry_price
        assert guaranteed_profit == 8_000.0
    
    def test_volatility_vs_trend_stop_selection(self):
        """변동성 vs 추세 손절가 선택"""
        entry_price = 50_000
        current_price = 52_000
        atr = 1_000
        
        # 케이스 1: 추세 손절가가 더 높음 (보수적)
        trend_stop_high = 49_000
        result1 = get_stop_loss_price(
            entry_price, current_price, atr, trend_stop_high, 'long'
        )
        assert result1['stop_type'] == 'trend'
        assert result1['stop_price'] == 49_000.0
        
        # 케이스 2: 변동성 손절가가 더 높음 (보수적)
        trend_stop_low = 47_000
        result2 = get_stop_loss_price(
            entry_price, current_price, atr, trend_stop_low, 'long'
        )
        assert result2['stop_type'] == 'volatility'
        assert result2['stop_price'] == 48_000.0
    
    def test_stop_loss_consistency_across_scenarios(self):
        """다양한 시나리오에서 일관성"""
        scenarios = [
            # (진입가, ATR, 예상 손실률)
            (50_000, 1_000, 0.04),  # 4%
            (100_000, 2_000, 0.04),  # 4%
            (10_000, 200, 0.04),  # 4%
        ]
        
        for entry, atr, expected_loss in scenarios:
            vol_stop = calculate_volatility_stop(entry, atr, 'long', 2.0)
            actual_loss = (entry - vol_stop) / entry
            
            assert abs(actual_loss - expected_loss) < 0.001
