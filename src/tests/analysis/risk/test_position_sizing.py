"""
포지션 사이징 모듈 테스트

테스트 대상:
- calculate_unit_size: 기본 유닛 계산 (터틀 방식)
- adjust_by_signal_strength: 신호 강도 조정
- calculate_position_size: 최종 포지션 크기 계산
- get_max_position_by_capital: 자본 제약 확인
"""

import pytest
from src.analysis.risk.position_sizing import (
    calculate_unit_size,
    adjust_by_signal_strength,
    calculate_position_size,
    get_max_position_by_capital
)


class TestCalculateUnitSize:
    """기본 유닛 계산 테스트"""
    
    def test_standard_case(self):
        """표준 케이스: 1천만원, ATR 1천원, 리스크 1%"""
        result = calculate_unit_size(10_000_000, 1_000, 0.01)
        
        assert result == 100
    
    def test_high_volatility_reduces_units(self):
        """고변동성 → 유닛 감소"""
        # ATR이 2배 → 유닛이 절반
        result = calculate_unit_size(10_000_000, 2_000, 0.01)
        
        assert result == 50
    
    def test_low_volatility_increases_units(self):
        """저변동성 → 유닛 증가"""
        # ATR이 절반 → 유닛이 2배
        result = calculate_unit_size(10_000_000, 500, 0.01)
        
        assert result == 200
    
    def test_higher_risk_increases_units(self):
        """높은 리스크 비율 → 유닛 증가"""
        # 리스크 2% → 유닛 2배
        result = calculate_unit_size(10_000_000, 1_000, 0.02)
        
        assert result == 200
    
    def test_lower_risk_decreases_units(self):
        """낮은 리스크 비율 → 유닛 감소"""
        # 리스크 0.5% → 유닛 절반
        result = calculate_unit_size(10_000_000, 1_000, 0.005)
        
        assert result == 50
    
    def test_small_account_balance(self):
        """소액 계좌"""
        result = calculate_unit_size(1_000_000, 1_000, 0.01)
        
        assert result == 10
    
    def test_large_account_balance(self):
        """대형 계좌"""
        result = calculate_unit_size(100_000_000, 1_000, 0.01)
        
        assert result == 1_000
    
    def test_rounding_down(self):
        """반올림 - 내림"""
        # 10,000,000 * 0.01 / 1,500 = 66.666...
        result = calculate_unit_size(10_000_000, 1_500, 0.01)
        
        assert result == 67  # 반올림
    
    def test_rounding_up(self):
        """반올림 - 올림"""
        # 10,000,000 * 0.01 / 1,200 = 83.333...
        result = calculate_unit_size(10_000_000, 1_200, 0.01)
        
        assert result == 83  # 반올림
    
    def test_zero_account_balance_raises_error(self):
        """계좌 잔고 0 → ValueError"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수여야"):
            calculate_unit_size(0, 1_000, 0.01)
    
    def test_negative_account_balance_raises_error(self):
        """계좌 잔고 음수 → ValueError"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수여야"):
            calculate_unit_size(-10_000_000, 1_000, 0.01)
    
    def test_zero_atr_raises_error(self):
        """ATR 0 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            calculate_unit_size(10_000_000, 0, 0.01)
    
    def test_negative_atr_raises_error(self):
        """ATR 음수 → ValueError"""
        with pytest.raises(ValueError, match="ATR은 양수여야"):
            calculate_unit_size(10_000_000, -1_000, 0.01)
    
    def test_risk_percentage_zero_raises_error(self):
        """리스크 비율 0 → ValueError"""
        with pytest.raises(ValueError, match="리스크 비율은 0~1 사이여야"):
            calculate_unit_size(10_000_000, 1_000, 0)
    
    def test_risk_percentage_negative_raises_error(self):
        """리스크 비율 음수 → ValueError"""
        with pytest.raises(ValueError, match="리스크 비율은 0~1 사이여야"):
            calculate_unit_size(10_000_000, 1_000, -0.01)
    
    def test_risk_percentage_over_100_raises_error(self):
        """리스크 비율 100% 초과 → ValueError"""
        with pytest.raises(ValueError, match="리스크 비율은 0~1 사이여야"):
            calculate_unit_size(10_000_000, 1_000, 1.5)
    
    def test_risk_percentage_exactly_100(self):
        """리스크 비율 정확히 100% → 허용"""
        result = calculate_unit_size(10_000_000, 1_000, 1.0)
        
        assert result == 10_000
    
    def test_invalid_account_balance_type_raises_error(self):
        """잘못된 account_balance 타입 → TypeError"""
        with pytest.raises(TypeError, match="account_balance는 숫자여야"):
            calculate_unit_size("10000000", 1_000, 0.01)
    
    def test_invalid_atr_type_raises_error(self):
        """잘못된 ATR 타입 → TypeError"""
        with pytest.raises(TypeError, match="atr은 숫자여야"):
            calculate_unit_size(10_000_000, "1000", 0.01)
    
    def test_invalid_risk_percentage_type_raises_error(self):
        """잘못된 risk_percentage 타입 → TypeError"""
        with pytest.raises(TypeError, match="risk_percentage는 숫자여야"):
            calculate_unit_size(10_000_000, 1_000, "0.01")
    
    def test_float_inputs_work(self):
        """실수 입력 → 정상 작동"""
        result = calculate_unit_size(10_000_000.0, 1_000.0, 0.01)
        
        assert result == 100


class TestAdjustBySignalStrength:
    """신호 강도 조정 테스트"""
    
    def test_strong_signal_100_percent(self):
        """강한 신호 (80점 이상) → 100%"""
        result = adjust_by_signal_strength(100, 85, 80)
        
        assert result == 100
    
    def test_threshold_signal_100_percent(self):
        """임계값 정확히 80점 → 100%"""
        result = adjust_by_signal_strength(100, 80, 80)
        
        assert result == 100
    
    def test_medium_high_signal_75_percent(self):
        """중상 신호 (70-80점) → 75%"""
        result = adjust_by_signal_strength(100, 75, 80)
        
        assert result == 75
    
    def test_medium_signal_50_percent(self):
        """중간 신호 (60-70점) → 50%"""
        result = adjust_by_signal_strength(100, 65, 80)
        
        assert result == 50
    
    def test_medium_low_signal_25_percent(self):
        """중하 신호 (50-60점) → 25%"""
        result = adjust_by_signal_strength(100, 55, 80)
        
        assert result == 25
    
    def test_weak_signal_zero_percent(self):
        """약한 신호 (50점 미만) → 0%"""
        result = adjust_by_signal_strength(100, 45, 80)
        
        assert result == 0
    
    def test_boundary_70_points(self):
        """경계값 70점 → 75%"""
        result = adjust_by_signal_strength(100, 70, 80)
        
        assert result == 75
    
    def test_boundary_60_points(self):
        """경계값 60점 → 50%"""
        result = adjust_by_signal_strength(100, 60, 80)
        
        assert result == 50
    
    def test_boundary_50_points(self):
        """경계값 50점 → 25%"""
        result = adjust_by_signal_strength(100, 50, 80)
        
        assert result == 25
    
    def test_boundary_49_points(self):
        """경계값 49점 → 0%"""
        result = adjust_by_signal_strength(100, 49, 80)
        
        assert result == 0
    
    def test_maximum_signal_100_points(self):
        """최고 신호 100점 → 100%"""
        result = adjust_by_signal_strength(100, 100, 80)
        
        assert result == 100
    
    def test_minimum_signal_0_points(self):
        """최저 신호 0점 → 0%"""
        result = adjust_by_signal_strength(100, 0, 80)
        
        assert result == 0
    
    def test_zero_base_units(self):
        """기본 유닛 0 → 0"""
        result = adjust_by_signal_strength(0, 85, 80)
        
        assert result == 0
    
    def test_custom_threshold_90(self):
        """커스텀 임계값 90점"""
        # 85점은 90점 미만이므로 75%
        result = adjust_by_signal_strength(100, 85, 90)
        
        assert result == 75
    
    def test_custom_threshold_60(self):
        """커스텀 임계값 60점"""
        # 65점은 60점 이상이므로 100%
        result = adjust_by_signal_strength(100, 65, 60)
        
        assert result == 100
    
    def test_large_base_units(self):
        """큰 기본 유닛"""
        result = adjust_by_signal_strength(1_000, 75, 80)
        
        assert result == 750
    
    def test_negative_base_units_raises_error(self):
        """음수 기본 유닛 → ValueError"""
        with pytest.raises(ValueError, match="기본 유닛은 음수일 수 없습니다"):
            adjust_by_signal_strength(-100, 85, 80)
    
    def test_signal_strength_negative_raises_error(self):
        """신호 강도 음수 → ValueError"""
        with pytest.raises(ValueError, match="신호 강도는 0-100 사이여야"):
            adjust_by_signal_strength(100, -10, 80)
    
    def test_signal_strength_over_100_raises_error(self):
        """신호 강도 100 초과 → ValueError"""
        with pytest.raises(ValueError, match="신호 강도는 0-100 사이여야"):
            adjust_by_signal_strength(100, 150, 80)
    
    def test_threshold_negative_raises_error(self):
        """임계값 음수 → ValueError"""
        with pytest.raises(ValueError, match="강도 임계값은 0-100 사이여야"):
            adjust_by_signal_strength(100, 85, -10)
    
    def test_threshold_over_100_raises_error(self):
        """임계값 100 초과 → ValueError"""
        with pytest.raises(ValueError, match="강도 임계값은 0-100 사이여야"):
            adjust_by_signal_strength(100, 85, 150)
    
    def test_invalid_base_units_type_raises_error(self):
        """잘못된 base_units 타입 → TypeError"""
        with pytest.raises(TypeError, match="base_units는 정수여야"):
            adjust_by_signal_strength(100.5, 85, 80)
    
    def test_invalid_signal_strength_type_raises_error(self):
        """잘못된 signal_strength 타입 → TypeError"""
        with pytest.raises(TypeError, match="signal_strength는 정수여야"):
            adjust_by_signal_strength(100, 85.5, 80)
    
    def test_invalid_threshold_type_raises_error(self):
        """잘못된 threshold 타입 → TypeError"""
        with pytest.raises(TypeError, match="strength_threshold는 정수여야"):
            adjust_by_signal_strength(100, 85, 80.5)


class TestCalculatePositionSize:
    """최종 포지션 크기 계산 테스트"""
    
    def test_standard_case(self):
        """표준 케이스"""
        result = calculate_position_size(10_000_000, 50_000, 1_000, 85)
        
        assert result['units'] == 1
        assert result['shares'] == 100
        assert result['total_value'] == 5_000_000.0
        assert result['risk_amount'] == 100_000.0
        assert result['position_percentage'] == 0.5
        assert result['unit_value'] == 5_000_000.0
    
    def test_weak_signal_reduces_shares(self):
        """약한 신호 → 주식 수 감소"""
        # 65점 = 50% 포지션
        result = calculate_position_size(10_000_000, 50_000, 1_000, 65)
        
        assert result['shares'] == 50
        assert result['total_value'] == 2_500_000.0
    
    def test_very_weak_signal_minimal_shares(self):
        """매우 약한 신호 → 최소 포지션"""
        # 55점 = 25% 포지션
        result = calculate_position_size(10_000_000, 50_000, 1_000, 55)
        
        assert result['shares'] == 25
        assert result['total_value'] == 1_250_000.0
    
    def test_filtered_signal_zero_shares(self):
        """필터링 신호 → 0주"""
        # 45점 = 0% 포지션
        result = calculate_position_size(10_000_000, 50_000, 1_000, 45)
        
        assert result['shares'] == 0
        assert result['total_value'] == 0.0
        assert result['position_percentage'] == 0.0
    
    def test_high_volatility_reduces_shares(self):
        """고변동성 → 주식 수 감소"""
        # ATR 2배 → 유닛 절반
        result = calculate_position_size(10_000_000, 50_000, 2_000, 85)
        
        assert result['shares'] == 50
        assert result['total_value'] == 2_500_000.0
    
    def test_expensive_stock(self):
        """고가 주식"""
        # 가격 100만원
        result = calculate_position_size(10_000_000, 1_000_000, 10_000, 85)
        
        assert result['shares'] == 10
        assert result['total_value'] == 10_000_000.0
        assert result['position_percentage'] == 1.0
    
    def test_cheap_stock(self):
        """저가 주식"""
        # 가격 1만원
        result = calculate_position_size(10_000_000, 10_000, 500, 85)
        
        assert result['shares'] == 200
        assert result['total_value'] == 2_000_000.0
    
    def test_higher_risk_percentage(self):
        """높은 리스크 비율"""
        # 2% 리스크
        result = calculate_position_size(10_000_000, 50_000, 1_000, 85, 0.02)
        
        assert result['shares'] == 200
        assert result['risk_amount'] == 200_000.0
    
    def test_default_signal_strength_is_80(self):
        """기본 신호 강도 80점"""
        result = calculate_position_size(10_000_000, 50_000, 1_000)
        
        assert result['shares'] == 100  # 80점 = 100%
    
    def test_default_risk_percentage_is_1_percent(self):
        """기본 리스크 비율 1%"""
        result = calculate_position_size(10_000_000, 50_000, 1_000, 85)
        
        assert result['risk_amount'] == 100_000.0
    
    def test_zero_current_price_raises_error(self):
        """현재가 0 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            calculate_position_size(10_000_000, 0, 1_000, 85)
    
    def test_negative_current_price_raises_error(self):
        """현재가 음수 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            calculate_position_size(10_000_000, -50_000, 1_000, 85)
    
    def test_invalid_current_price_type_raises_error(self):
        """잘못된 current_price 타입 → TypeError"""
        with pytest.raises(TypeError, match="current_price는 숫자여야"):
            calculate_position_size(10_000_000, "50000", 1_000, 85)
    
    def test_result_has_all_required_keys(self):
        """결과에 모든 필수 키 포함"""
        result = calculate_position_size(10_000_000, 50_000, 1_000, 85)
        
        required_keys = [
            'units', 'shares', 'total_value', 
            'risk_amount', 'position_percentage', 'unit_value'
        ]
        
        for key in required_keys:
            assert key in result
    
    def test_units_always_one_for_initial_entry(self):
        """초기 진입은 항상 1유닛"""
        result = calculate_position_size(10_000_000, 50_000, 1_000, 85)
        
        assert result['units'] == 1


class TestGetMaxPositionByCapital:
    """자본 제약 확인 테스트"""
    
    def test_standard_case_25_percent(self):
        """표준 케이스: 25% 제한"""
        result = get_max_position_by_capital(10_000_000, 50_000, 0.25)
        
        assert result == 50
    
    def test_conservative_20_percent(self):
        """보수적: 20% 제한"""
        result = get_max_position_by_capital(10_000_000, 50_000, 0.20)
        
        assert result == 40
    
    def test_aggressive_30_percent(self):
        """공격적: 30% 제한"""
        result = get_max_position_by_capital(10_000_000, 50_000, 0.30)
        
        assert result == 60
    
    def test_expensive_stock(self):
        """고가 주식"""
        # 100만원 주식, 25% = 250만원 = 2주
        result = get_max_position_by_capital(10_000_000, 1_000_000, 0.25)
        
        assert result == 2
    
    def test_cheap_stock(self):
        """저가 주식"""
        # 1만원 주식, 25% = 250만원 = 250주
        result = get_max_position_by_capital(10_000_000, 10_000, 0.25)
        
        assert result == 250
    
    def test_small_account(self):
        """소액 계좌"""
        # 100만원 계좌, 25% = 25만원 / 5만원 = 5주
        result = get_max_position_by_capital(1_000_000, 50_000, 0.25)
        
        assert result == 5
    
    def test_large_account(self):
        """대형 계좌"""
        # 1억원 계좌, 25% = 2500만원 / 5만원 = 500주
        result = get_max_position_by_capital(100_000_000, 50_000, 0.25)
        
        assert result == 500
    
    def test_floor_division_rounds_down(self):
        """내림 처리 (보수적)"""
        # 10,000,000 * 0.25 / 60,000 = 41.666... → 41
        result = get_max_position_by_capital(10_000_000, 60_000, 0.25)
        
        assert result == 41
    
    def test_exact_division(self):
        """정확히 나누어떨어지는 경우"""
        # 10,000,000 * 0.25 / 25,000 = 100
        result = get_max_position_by_capital(10_000_000, 25_000, 0.25)
        
        assert result == 100
    
    def test_default_ratio_is_25_percent(self):
        """기본 비율 25%"""
        result = get_max_position_by_capital(10_000_000, 50_000)
        
        assert result == 50
    
    def test_very_expensive_stock_limits_shares(self):
        """매우 고가 주식 → 극소 주식"""
        # 500만원 주식, 25% = 250만원 = 0.5주 → 0주
        result = get_max_position_by_capital(10_000_000, 5_000_000, 0.25)
        
        assert result == 0
    
    def test_zero_account_balance_raises_error(self):
        """계좌 잔고 0 → ValueError"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수여야"):
            get_max_position_by_capital(0, 50_000, 0.25)
    
    def test_negative_account_balance_raises_error(self):
        """계좌 잔고 음수 → ValueError"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수여야"):
            get_max_position_by_capital(-10_000_000, 50_000, 0.25)
    
    def test_zero_current_price_raises_error(self):
        """현재가 0 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            get_max_position_by_capital(10_000_000, 0, 0.25)
    
    def test_negative_current_price_raises_error(self):
        """현재가 음수 → ValueError"""
        with pytest.raises(ValueError, match="현재가는 양수여야"):
            get_max_position_by_capital(10_000_000, -50_000, 0.25)
    
    def test_ratio_zero_raises_error(self):
        """비율 0 → ValueError"""
        with pytest.raises(ValueError, match="최대 자본 비율은 0~1 사이여야"):
            get_max_position_by_capital(10_000_000, 50_000, 0)
    
    def test_ratio_negative_raises_error(self):
        """비율 음수 → ValueError"""
        with pytest.raises(ValueError, match="최대 자본 비율은 0~1 사이여야"):
            get_max_position_by_capital(10_000_000, 50_000, -0.25)
    
    def test_ratio_over_100_raises_error(self):
        """비율 100% 초과 → ValueError"""
        with pytest.raises(ValueError, match="최대 자본 비율은 0~1 사이여야"):
            get_max_position_by_capital(10_000_000, 50_000, 1.5)
    
    def test_ratio_exactly_100_percent(self):
        """비율 정확히 100% → 허용"""
        result = get_max_position_by_capital(10_000_000, 50_000, 1.0)
        
        assert result == 200
    
    def test_invalid_account_balance_type_raises_error(self):
        """잘못된 account_balance 타입 → TypeError"""
        with pytest.raises(TypeError, match="account_balance는 숫자여야"):
            get_max_position_by_capital("10000000", 50_000, 0.25)
    
    def test_invalid_current_price_type_raises_error(self):
        """잘못된 current_price 타입 → TypeError"""
        with pytest.raises(TypeError, match="current_price는 숫자여야"):
            get_max_position_by_capital(10_000_000, "50000", 0.25)
    
    def test_invalid_ratio_type_raises_error(self):
        """잘못된 ratio 타입 → TypeError"""
        with pytest.raises(TypeError, match="max_capital_ratio는 숫자여야"):
            get_max_position_by_capital(10_000_000, 50_000, "0.25")


class TestIntegration:
    """통합 테스트"""
    
    def test_position_sizing_flow(self):
        """전체 포지션 사이징 흐름"""
        # 1. 기본 유닛 계산
        base_units = calculate_unit_size(10_000_000, 1_000, 0.01)
        assert base_units == 100
        
        # 2. 신호 강도 조정
        adjusted_units = adjust_by_signal_strength(base_units, 85, 80)
        assert adjusted_units == 100
        
        # 3. 자본 제약 확인
        max_shares = get_max_position_by_capital(10_000_000, 50_000, 0.25)
        assert max_shares == 50
        
        # 4. 최종 포지션 (min 선택)
        final_shares = min(adjusted_units, max_shares)
        assert final_shares == 50
    
    def test_volatility_based_sizing_vs_capital_constraint(self):
        """변동성 기반 vs 자본 제약"""
        account = 10_000_000
        price = 50_000
        
        # 저변동성 → 큰 포지션
        vol_based = calculate_unit_size(account, 500, 0.01)
        assert vol_based == 200
        
        # 자본 제약 25%
        capital_based = get_max_position_by_capital(account, price, 0.25)
        assert capital_based == 50
        
        # 최종은 더 작은 값
        final = min(vol_based, capital_based)
        assert final == 50  # 자본 제약이 더 엄격
    
    def test_signal_strength_scaling(self):
        """신호 강도별 스케일링"""
        base_units = 100
        
        # 90점 → 100%
        result_90 = adjust_by_signal_strength(base_units, 90, 80)
        assert result_90 == 100
        
        # 75점 → 75%
        result_75 = adjust_by_signal_strength(base_units, 75, 80)
        assert result_75 == 75
        
        # 65점 → 50%
        result_65 = adjust_by_signal_strength(base_units, 65, 80)
        assert result_65 == 50
        
        # 55점 → 25%
        result_55 = adjust_by_signal_strength(base_units, 55, 80)
        assert result_55 == 25
        
        # 순서 확인
        assert result_90 > result_75 > result_65 > result_55
    
    def test_complete_position_calculation(self):
        """완전한 포지션 계산 예제"""
        result = calculate_position_size(
            account_balance=10_000_000,
            current_price=50_000,
            atr=1_000,
            signal_strength=85,
            risk_percentage=0.01
        )
        
        # 변동성 기반 포지션 검증
        assert result['shares'] == 100
        assert result['total_value'] == 5_000_000.0
        assert result['position_percentage'] == 0.5
        
        # 자본 제약 확인 (별도)
        max_by_capital = get_max_position_by_capital(10_000_000, 50_000, 0.25)
        assert max_by_capital == 50
        
        # 최종 포지션은 둘 중 작은 값
        final_shares = min(result['shares'], max_by_capital)
        assert final_shares == 50  # 자본 제약에 걸림
        
        # 실제 투자 금액
        final_value = final_shares * 50_000
        assert final_value == 2_500_000  # 250만원 (계좌의 25%)
    
    def test_risk_consistency_across_volatility(self):
        """변동성 변화에도 리스크 일정 유지"""
        account = 10_000_000
        risk_pct = 0.01
        
        # 저변동성
        units_low = calculate_unit_size(account, 500, risk_pct)
        risk_low = units_low * 500
        
        # 중변동성
        units_mid = calculate_unit_size(account, 1_000, risk_pct)
        risk_mid = units_mid * 1_000
        
        # 고변동성
        units_high = calculate_unit_size(account, 2_000, risk_pct)
        risk_high = units_high * 2_000
        
        # 모든 경우 리스크 동일 (계좌의 1%)
        expected_risk = account * risk_pct
        assert abs(risk_low - expected_risk) < 100
        assert abs(risk_mid - expected_risk) < 100
        assert abs(risk_high - expected_risk) < 100
