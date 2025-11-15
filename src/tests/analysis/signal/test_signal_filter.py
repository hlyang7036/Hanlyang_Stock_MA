"""
신호 필터링 모듈 테스트

테스트 대상:
- check_strength_filter: 신호 강도 필터
- check_volatility_filter: 변동성 필터
- check_trend_filter: 추세 필터
- check_conflicting_signals: 상충 신호 체크
- apply_signal_filters: 종합 필터링
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.signal.filter import (
    check_strength_filter,
    check_volatility_filter,
    check_trend_filter,
    check_conflicting_signals,
    apply_signal_filters
)


class TestCheckStrengthFilter:
    """신호 강도 필터 테스트"""
    
    def test_all_signals_pass_low_threshold(self):
        """낮은 임계값 → 대부분 신호 통과"""
        data = pd.DataFrame({
            'Signal_Strength': [30, 40, 50, 60, 70]
        })
        
        passed = check_strength_filter(data, min_strength=30)
        
        assert all(passed)
    
    def test_filter_weak_signals(self):
        """약한 신호 필터링"""
        data = pd.DataFrame({
            'Signal_Strength': [20, 40, 50, 60, 80]
        })
        
        passed = check_strength_filter(data, min_strength=50)
        
        assert passed[0] == False  # 20점 제외
        assert passed[1] == False  # 40점 제외
        assert passed[2] == True   # 50점 통과
        assert passed[3] == True   # 60점 통과
        assert passed[4] == True   # 80점 통과
    
    def test_all_signals_fail_high_threshold(self):
        """높은 임계값 → 모든 신호 실패"""
        data = pd.DataFrame({
            'Signal_Strength': [30, 40, 50, 60, 70]
        })
        
        passed = check_strength_filter(data, min_strength=90)
        
        assert not any(passed)
    
    def test_exact_threshold_passes(self):
        """임계값과 정확히 같은 값은 통과"""
        data = pd.DataFrame({
            'Signal_Strength': [49, 50, 51]
        })
        
        passed = check_strength_filter(data, min_strength=50)
        
        assert passed[0] == False
        assert passed[1] == True   # 정확히 50 → 통과
        assert passed[2] == True
    
    def test_missing_column_raises_error(self):
        """필수 컬럼 누락 시 ValueError"""
        data = pd.DataFrame({
            'Other_Column': [1, 2, 3]
        })
        
        with pytest.raises(ValueError, match="Signal_Strength 컬럼이 필요합니다"):
            check_strength_filter(data)
    
    def test_invalid_min_strength_raises_error(self):
        """잘못된 min_strength 값"""
        data = pd.DataFrame({
            'Signal_Strength': [50, 60, 70]
        })
        
        # 음수
        with pytest.raises(ValueError, match="0-100 범위여야"):
            check_strength_filter(data, min_strength=-10)
        
        # 100 초과
        with pytest.raises(ValueError, match="0-100 범위여야"):
            check_strength_filter(data, min_strength=150)
    
    def test_invalid_input_type_raises_error(self):
        """잘못된 입력 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            check_strength_filter([1, 2, 3])
    
    def test_empty_dataframe_returns_empty_series(self):
        """빈 DataFrame → 빈 Series"""
        data = pd.DataFrame({
            'Signal_Strength': []
        })
        
        passed = check_strength_filter(data)
        
        assert len(passed) == 0
    
    def test_default_threshold_is_50(self):
        """기본 임계값 50점"""
        data = pd.DataFrame({
            'Signal_Strength': [45, 50, 55]
        })
        
        passed = check_strength_filter(data)  # min_strength 기본값
        
        assert passed[0] == False
        assert passed[1] == True
        assert passed[2] == True


class TestCheckVolatilityFilter:
    """변동성 필터 테스트"""
    
    def test_all_signals_pass_high_percentile(self):
        """높은 백분위수 → 대부분 통과"""
        data = pd.DataFrame({
            'ATR': [1.0, 2.0, 3.0, 4.0, 5.0]
        })
        
        passed = check_volatility_filter(data, max_atr_percentile=90)
        
        # 상위 10%만 제외되므로 4/5 통과
        assert passed.sum() >= 4
    
    def test_filter_high_volatility(self):
        """고변동성 신호 필터링"""
        data = pd.DataFrame({
            'ATR': np.arange(1, 101)  # 1부터 100까지
        })
        
        passed = check_volatility_filter(data, max_atr_percentile=90)
        
        # 상위 10% (91-100) 제외, 하위 90% (1-90) 통과
        assert passed.sum() == 90
    
    def test_extreme_low_percentile_filters_most(self):
        """낮은 백분위수 → 대부분 필터링"""
        data = pd.DataFrame({
            'ATR': np.arange(1, 101)
        })
        
        passed = check_volatility_filter(data, max_atr_percentile=20)
        
        # 하위 20%만 통과
        assert passed.sum() == 20
    
    def test_percentile_100_passes_all(self):
        """백분위수 100 → 모두 통과"""
        data = pd.DataFrame({
            'ATR': [1.0, 5.0, 10.0, 15.0, 20.0]
        })
        
        passed = check_volatility_filter(data, max_atr_percentile=100)
        
        assert all(passed)
    
    def test_missing_column_raises_error(self):
        """필수 컬럼 누락 시 ValueError"""
        data = pd.DataFrame({
            'Other_Column': [1, 2, 3]
        })
        
        with pytest.raises(ValueError, match="ATR 컬럼이 필요합니다"):
            check_volatility_filter(data)
    
    def test_invalid_percentile_raises_error(self):
        """잘못된 백분위수 값"""
        data = pd.DataFrame({
            'ATR': [1.0, 2.0, 3.0]
        })
        
        # 음수
        with pytest.raises(ValueError, match="0-100 범위여야"):
            check_volatility_filter(data, max_atr_percentile=-10)
        
        # 100 초과
        with pytest.raises(ValueError, match="0-100 범위여야"):
            check_volatility_filter(data, max_atr_percentile=150)
    
    def test_invalid_input_type_raises_error(self):
        """잘못된 입력 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            check_volatility_filter("not a dataframe")
    
    def test_default_percentile_is_90(self):
        """기본 백분위수 90%"""
        data = pd.DataFrame({
            'ATR': np.arange(1, 101)
        })
        
        passed = check_volatility_filter(data)  # 기본값
        
        assert passed.sum() == 90


class TestCheckTrendFilter:
    """추세 필터 테스트"""
    
    def test_strong_upward_trend_passes(self):
        """강한 상승 추세 → 통과"""
        data = pd.DataFrame({
            'Slope_EMA_40': [0.5, 0.8, 1.0, 1.5, 2.0]
        })
        
        passed = check_trend_filter(data, min_slope=0.1)
        
        assert all(passed)
    
    def test_strong_downward_trend_passes(self):
        """강한 하락 추세 → 통과 (절댓값 평가)"""
        data = pd.DataFrame({
            'Slope_EMA_40': [-0.5, -0.8, -1.0, -1.5, -2.0]
        })
        
        passed = check_trend_filter(data, min_slope=0.1)
        
        assert all(passed)
    
    def test_filter_weak_trends(self):
        """약한 추세 필터링"""
        data = pd.DataFrame({
            'Slope_EMA_40': [0.05, 0.08, 0.10, 0.15, 0.20]
        })
        
        passed = check_trend_filter(data, min_slope=0.10)
        
        assert passed[0] == False  # 0.05 제외
        assert passed[1] == False  # 0.08 제외
        assert passed[2] == True   # 0.10 통과
        assert passed[3] == True   # 0.15 통과
        assert passed[4] == True   # 0.20 통과
    
    def test_flat_trends_filtered(self):
        """횡보 (0 근처) 필터링"""
        data = pd.DataFrame({
            'Slope_EMA_40': [-0.02, -0.01, 0.0, 0.01, 0.02]
        })
        
        passed = check_trend_filter(data, min_slope=0.05)
        
        assert not any(passed)  # 모두 0.05 미만
    
    def test_exact_threshold_passes(self):
        """임계값과 정확히 같은 값은 통과"""
        data = pd.DataFrame({
            'Slope_EMA_40': [0.09, 0.10, 0.11, -0.10]
        })
        
        passed = check_trend_filter(data, min_slope=0.10)
        
        assert passed[0] == False
        assert passed[1] == True   # 정확히 0.10
        assert passed[2] == True
        assert passed[3] == True   # -0.10의 절댓값 0.10
    
    def test_missing_column_raises_error(self):
        """필수 컬럼 누락 시 ValueError"""
        data = pd.DataFrame({
            'Other_Column': [1, 2, 3]
        })
        
        with pytest.raises(ValueError, match="Slope_EMA_40 컬럼이 필요합니다"):
            check_trend_filter(data)
    
    def test_negative_min_slope_raises_error(self):
        """음수 min_slope → ValueError"""
        data = pd.DataFrame({
            'Slope_EMA_40': [0.1, 0.2, 0.3]
        })
        
        with pytest.raises(ValueError, match="0 이상이어야"):
            check_trend_filter(data, min_slope=-0.1)
    
    def test_invalid_input_type_raises_error(self):
        """잘못된 입력 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            check_trend_filter({'key': 'value'})
    
    def test_default_min_slope_is_0_1(self):
        """기본 최소 기울기 0.1"""
        data = pd.DataFrame({
            'Slope_EMA_40': [0.05, 0.10, 0.15]
        })
        
        passed = check_trend_filter(data)  # 기본값
        
        assert passed[0] == False
        assert passed[1] == True
        assert passed[2] == True


class TestCheckConflictingSignals:
    """상충 신호 체크 테스트"""
    
    def test_no_conflict_with_entry_only(self):
        """진입 신호만 있을 때 → 상충 없음"""
        data = pd.DataFrame({
            'Entry_Signal': [1, 0, 2, 0, 1],
            'Exit_Signal': [0, 0, 0, 0, 0]
        })
        
        passed = check_conflicting_signals(data)
        
        assert all(passed)
    
    def test_no_conflict_with_exit_only(self):
        """청산 신호만 있을 때 → 상충 없음"""
        data = pd.DataFrame({
            'Entry_Signal': [0, 0, 0, 0, 0],
            'Exit_Signal': [1, 0, 2, 0, 3]
        })
        
        passed = check_conflicting_signals(data)
        
        assert all(passed)
    
    def test_detect_simultaneous_signals(self):
        """진입과 청산 동시 발생 감지"""
        data = pd.DataFrame({
            'Entry_Signal': [1, 0, 2, 1, 0],
            'Exit_Signal': [0, 0, 3, 2, 0]
        })
        
        passed = check_conflicting_signals(data)
        
        assert passed[0] == True   # 진입만
        assert passed[1] == True   # 둘 다 없음
        assert passed[2] == False  # 충돌!
        assert passed[3] == False  # 충돌!
        assert passed[4] == True   # 둘 다 없음
    
    def test_no_signals_passes(self):
        """신호 없을 때 → 상충 없음"""
        data = pd.DataFrame({
            'Entry_Signal': [0, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        passed = check_conflicting_signals(data)
        
        assert all(passed)
    
    def test_missing_both_columns_passes_all(self):
        """Entry/Exit 컬럼 모두 없으면 → 모두 통과"""
        data = pd.DataFrame({
            'Other_Column': [1, 2, 3]
        })
        
        passed = check_conflicting_signals(data)
        
        assert all(passed)
    
    def test_missing_entry_column_only(self):
        """Entry_Signal만 없을 때"""
        data = pd.DataFrame({
            'Exit_Signal': [1, 2, 3]
        })
        
        passed = check_conflicting_signals(data)
        
        # Exit만 있으면 상충 없음
        assert all(passed)
    
    def test_missing_exit_column_only(self):
        """Exit_Signal만 없을 때"""
        data = pd.DataFrame({
            'Entry_Signal': [1, 2, 3]
        })
        
        passed = check_conflicting_signals(data)
        
        # Entry만 있으면 상충 없음
        assert all(passed)
    
    def test_invalid_input_type_raises_error(self):
        """잘못된 입력 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            check_conflicting_signals([1, 2, 3])
    
    def test_various_signal_values(self):
        """다양한 신호 값 (0이 아닌 모든 값 = 신호 있음)"""
        data = pd.DataFrame({
            'Entry_Signal': [1, 2, -1, 0, 5],
            'Exit_Signal': [0, 0, 3, 4, 0]
        })
        
        passed = check_conflicting_signals(data)
        
        assert passed[0] == True   # Entry만
        assert passed[1] == True   # Entry만
        assert passed[2] == False  # 충돌 (Entry=-1, Exit=3)
        assert passed[3] == True   # Exit만
        assert passed[4] == True   # Entry만


class TestApplySignalFilters:
    """종합 필터링 테스트"""
    
    def test_all_filters_enabled_by_default(self):
        """기본값으로 모든 필터 활성화"""
        data = pd.DataFrame({
            'Signal_Strength': [70, 80, 90],
            'ATR': [2.0, 2.5, 3.0],
            'Slope_EMA_40': [0.2, 0.3, 0.4],
            'Entry_Signal': [1, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        result = apply_signal_filters(data)
        
        assert 'Filter_Strength' in result.columns
        assert 'Filter_Volatility' in result.columns
        assert 'Filter_Trend' in result.columns
        assert 'Filter_Conflict' in result.columns
        assert 'Filter_Passed' in result.columns
        assert 'Filter_Reasons' in result.columns
    
    def test_perfect_signals_pass_all_filters(self):
        """완벽한 신호 → 모든 필터 통과"""
        # 충분한 데이터로 백분위수 계산이 정상 작동하도록 함
        # 처음 5개 행이 테스트 대상, 나머지는 백분위수 계산을 위한 더미 데이터
        data = pd.DataFrame({
            'Signal_Strength': [90, 85, 80, 75, 70, 60, 50, 40, 30, 20],
            'ATR': [2.0, 2.1, 2.2, 2.3, 2.4, 3.0, 3.5, 4.0, 4.5, 5.0],  # 처음 5개는 50% 이하 백분위
            'Slope_EMA_40': [0.5, 0.6, 0.7, 0.8, 0.9, 0.4, 0.3, 0.2, 0.15, 0.1],
            'Entry_Signal': [1, 2, 0, 1, 0, 0, 0, 0, 0, 0],
            'Exit_Signal': [0, 0, 1, 0, 1, 0, 0, 0, 0, 0]
        })
        
        result = apply_signal_filters(data, min_strength=70)
        
        # 처음 5개 행만 검증 (모든 필터 통과해야 함)
        first_five = result.iloc[:5]
        assert all(first_five['Filter_Passed']), \
            f"실패한 행: {first_five[~first_five['Filter_Passed']][['Filter_Strength', 'Filter_Volatility', 'Filter_Trend', 'Filter_Conflict', 'Filter_Reasons']]}"
    
    def test_weak_signals_fail_strength_filter(self):
        """약한 신호 → 강도 필터 실패"""
        data = pd.DataFrame({
            'Signal_Strength': [30, 40, 50],
            'ATR': [2.0, 2.5, 3.0],
            'Slope_EMA_40': [0.2, 0.3, 0.4],
            'Entry_Signal': [1, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        result = apply_signal_filters(data, min_strength=60)
        
        assert not any(result['Filter_Passed'])
        assert all(result['Filter_Reasons'].str.contains('강도 부족'))
    
    def test_high_volatility_fails_filter(self):
        """고변동성 → 변동성 필터 실패"""
        # 100개 데이터로 백분위수 계산
        np.random.seed(42)
        data = pd.DataFrame({
            'Signal_Strength': [70] * 100,
            'ATR': np.random.uniform(1, 10, 100),
            'Slope_EMA_40': [0.2] * 100,
            'Entry_Signal': [1] * 100,
            'Exit_Signal': [0] * 100
        })
        
        result = apply_signal_filters(data)
        
        # 상위 10% (90 백분위 초과)는 실패해야 함
        failed_volatility = ~result['Filter_Volatility']
        assert failed_volatility.sum() >= 5  # 최소 5% 정도는 실패
    
    def test_weak_trend_fails_filter(self):
        """약한 추세 → 추세 필터 실패"""
        data = pd.DataFrame({
            'Signal_Strength': [70, 80, 90],
            'ATR': [2.0, 2.5, 3.0],
            'Slope_EMA_40': [0.05, 0.06, 0.07],  # 모두 0.1 미만
            'Entry_Signal': [1, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        result = apply_signal_filters(data)
        
        assert not any(result['Filter_Passed'])
        assert all(result['Filter_Reasons'].str.contains('약한 추세'))
    
    def test_conflicting_signals_fail_filter(self):
        """상충 신호 → 상충 필터 실패"""
        data = pd.DataFrame({
            'Signal_Strength': [70, 80, 90],
            'ATR': [2.0, 2.5, 3.0],
            'Slope_EMA_40': [0.2, 0.3, 0.4],
            'Entry_Signal': [1, 1, 1],
            'Exit_Signal': [1, 1, 1]  # 모두 충돌
        })
        
        result = apply_signal_filters(data)
        
        assert not any(result['Filter_Passed'])
        assert all(result['Filter_Reasons'].str.contains('신호 상충'))
    
    def test_selective_filters(self):
        """선택적 필터 적용"""
        data = pd.DataFrame({
            'Signal_Strength': [30, 40, 50],  # 약한 강도
            'ATR': [2.0, 2.5, 3.0],
            'Slope_EMA_40': [0.05, 0.06, 0.07],  # 약한 추세
            'Entry_Signal': [1, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        # 강도 필터만 활성화
        result = apply_signal_filters(
            data,
            min_strength=60,
            enable_filters={'strength': True, 'volatility': False, 'trend': False, 'conflict': False}
        )
        
        # 강도 필터만 적용되므로 모두 실패
        assert not any(result['Filter_Passed'])
        assert all(result['Filter_Reasons'] == '강도 부족')
    
    def test_disable_all_filters_passes_all(self):
        """모든 필터 비활성화 → 모두 통과"""
        data = pd.DataFrame({
            'Signal_Strength': [10, 20, 30],  # 매우 약함
            'ATR': [100, 200, 300],  # 매우 높음
            'Slope_EMA_40': [0.01, 0.02, 0.03],  # 매우 약함
            'Entry_Signal': [1, 1, 1],
            'Exit_Signal': [1, 1, 1]  # 충돌
        })
        
        result = apply_signal_filters(
            data,
            enable_filters={'strength': False, 'volatility': False, 'trend': False, 'conflict': False}
        )
        
        assert all(result['Filter_Passed'])
    
    def test_filter_reasons_accuracy(self):
        """필터링 이유 정확성"""
        data = pd.DataFrame({
            'Signal_Strength': [30],  # 강도 부족
            'ATR': [1.0],
            'Slope_EMA_40': [0.05],  # 약한 추세
            'Entry_Signal': [1],
            'Exit_Signal': [1]  # 상충
        })
        
        result = apply_signal_filters(data, min_strength=50)
        
        reasons = result['Filter_Reasons'].iloc[0]
        assert '강도 부족' in reasons
        assert '약한 추세' in reasons
        assert '신호 상충' in reasons
    
    def test_passed_signals_have_no_reasons(self):
        """통과한 신호는 이유 없음"""
        data = pd.DataFrame({
            'Signal_Strength': [80, 90],
            'ATR': [2.0, 2.5],
            'Slope_EMA_40': [0.3, 0.4],
            'Entry_Signal': [1, 0],
            'Exit_Signal': [0, 1]
        })
        
        result = apply_signal_filters(data)
        
        passed_signals = result[result['Filter_Passed']]
        assert all(passed_signals['Filter_Reasons'] == '')
    
    def test_invalid_input_type_raises_error(self):
        """잘못된 입력 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            apply_signal_filters("not a dataframe")
    
    def test_missing_columns_handles_gracefully(self):
        """필수 컬럼 누락 시 해당 필터만 통과 처리"""
        # ATR만 없는 경우
        data = pd.DataFrame({
            'Signal_Strength': [70, 80, 90],
            'Slope_EMA_40': [0.2, 0.3, 0.4],
            'Entry_Signal': [1, 0, 0],
            'Exit_Signal': [0, 0, 0]
        })
        
        result = apply_signal_filters(data)
        
        # 변동성 필터를 제외한 나머지는 정상 작동
        assert 'Filter_Volatility' in result.columns
        # 경고 로그 발생하지만 처리는 계속됨
    
    def test_empty_dataframe(self):
        """빈 DataFrame 처리"""
        data = pd.DataFrame({
            'Signal_Strength': [],
            'ATR': [],
            'Slope_EMA_40': [],
            'Entry_Signal': [],
            'Exit_Signal': []
        })
        
        result = apply_signal_filters(data)
        
        assert len(result) == 0
        assert 'Filter_Passed' in result.columns


class TestIntegration:
    """통합 테스트 - 실제 데이터 흐름"""
    
    def test_full_filtering_pipeline(self):
        """전체 필터링 파이프라인"""
        np.random.seed(42)
        
        # 100개의 신호 생성
        data = pd.DataFrame({
            'Signal_Strength': np.random.randint(20, 100, 100),
            'ATR': np.random.uniform(1, 10, 100),
            'Slope_EMA_40': np.random.uniform(-0.5, 0.5, 100),
            'Entry_Signal': np.random.choice([0, 1, 2], 100),
            'Exit_Signal': np.random.choice([0, 1, 2, 3], 100)
        })
        
        # 필터링 적용
        result = apply_signal_filters(data, min_strength=60)
        
        # 결과 검증
        assert len(result) == 100
        assert 'Filter_Passed' in result.columns
        
        # 통과한 신호 수 확인
        passed_count = result['Filter_Passed'].sum()
        assert 0 <= passed_count <= 100
        
        # 통과한 신호는 모든 개별 필터 통과
        passed_signals = result[result['Filter_Passed']]
        if len(passed_signals) > 0:
            assert all(passed_signals['Filter_Strength'])
            assert all(passed_signals['Filter_Volatility'])
            assert all(passed_signals['Filter_Trend'])
            assert all(passed_signals['Filter_Conflict'])
    
    def test_progressive_filtering(self):
        """단계별 필터링 효과"""
        data = pd.DataFrame({
            'Signal_Strength': [90, 80, 70, 60, 50, 40, 30, 20],
            'ATR': [1, 2, 3, 4, 5, 6, 7, 8],
            'Slope_EMA_40': [0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05, 0.01],
            'Entry_Signal': [1, 1, 1, 1, 0, 0, 0, 0],
            'Exit_Signal': [0, 0, 0, 0, 0, 0, 0, 0]
        })
        
        # 단계별 필터 강도 조정
        loose = apply_signal_filters(data, min_strength=30)
        medium = apply_signal_filters(data, min_strength=50)
        strict = apply_signal_filters(data, min_strength=70)
        
        # 엄격할수록 통과 신호 감소
        assert loose['Filter_Passed'].sum() >= medium['Filter_Passed'].sum()
        assert medium['Filter_Passed'].sum() >= strict['Filter_Passed'].sum()
    
    def test_filter_combination_effects(self):
        """필터 조합 효과"""
        data = pd.DataFrame({
            'Signal_Strength': [80] * 10,
            'ATR': [2.0] * 10,
            'Slope_EMA_40': [0.3] * 10,
            'Entry_Signal': [1] * 10,
            'Exit_Signal': [0] * 10
        })
        
        # 필터 없음
        no_filter = apply_signal_filters(
            data,
            enable_filters={'strength': False, 'volatility': False, 'trend': False, 'conflict': False}
        )
        
        # 강도 필터만
        only_strength = apply_signal_filters(
            data,
            min_strength=70,
            enable_filters={'strength': True, 'volatility': False, 'trend': False, 'conflict': False}
        )
        
        # 모든 필터
        all_filters = apply_signal_filters(data, min_strength=70)
        
        # 필터가 많을수록 통과 신호 감소 (또는 동일)
        assert no_filter['Filter_Passed'].sum() >= only_strength['Filter_Passed'].sum()
        assert only_strength['Filter_Passed'].sum() >= all_filters['Filter_Passed'].sum()
