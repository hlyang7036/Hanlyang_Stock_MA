"""
스테이지 분석 모듈 테스트

Tests:
    TestDetermineMAArrangement: 이동평균선 배열 판단 테스트
    TestDetectMACDZeroCross: MACD 0선 교차 감지 테스트
    TestDetermineStage: 스테이지 판단 테스트
    TestDetectStageTransition: 스테이지 전환 감지 테스트
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.stage import (
    determine_ma_arrangement,
    detect_macd_zero_cross,
    determine_stage,
    detect_stage_transition,
    calculate_ma_spread,
    check_ma_slope,
    get_stage_strategy
)


class TestDetermineMAArrangement:
    """이동평균선 배열 판단 테스트"""
    
    def test_arrangement_1_perfect_bull(self):
        """
        패턴 1: 단기 > 중기 > 장기 (완전 정배열)
        상승장의 전형적인 패턴
        """
        df = pd.DataFrame({
            'EMA_5': [110, 115, 120],
            'EMA_20': [105, 108, 112],
            'EMA_40': [100, 102, 105]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert len(arrangement) == 3
        assert all(arrangement == 1), "모든 시점이 패턴 1이어야 함"
    
    def test_arrangement_2_early_decline(self):
        """
        패턴 2: 중기 > 단기 > 장기
        하락 변화기1, 단기선이 중기선 아래로
        """
        df = pd.DataFrame({
            'EMA_5': [105, 106, 107],
            'EMA_20': [110, 112, 114],
            'EMA_40': [100, 102, 104]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert all(arrangement == 2), "모든 시점이 패턴 2여야 함"
    
    def test_arrangement_3_decline_phase(self):
        """
        패턴 3: 중기 > 장기 > 단기
        하락 변화기2, 단기선이 장기선 아래로
        """
        df = pd.DataFrame({
            'EMA_5': [95, 96, 97],
            'EMA_20': [110, 111, 112],
            'EMA_40': [100, 101, 102]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert all(arrangement == 3), "모든 시점이 패턴 3이어야 함"
    
    def test_arrangement_4_perfect_bear(self):
        """
        패턴 4: 장기 > 중기 > 단기 (완전 역배열)
        하락장의 전형적인 패턴
        """
        df = pd.DataFrame({
            'EMA_5': [90, 88, 85],
            'EMA_20': [95, 93, 90],
            'EMA_40': [100, 98, 96]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert all(arrangement == 4), "모든 시점이 패턴 4여야 함"
    
    def test_arrangement_5_early_rise(self):
        """
        패턴 5: 장기 > 단기 > 중기
        상승 변화기1, 단기선이 중기선 위로
        """
        df = pd.DataFrame({
            'EMA_5': [95, 96, 97],
            'EMA_20': [90, 91, 92],
            'EMA_40': [100, 101, 102]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert all(arrangement == 5), "모든 시점이 패턴 5여야 함"
    
    def test_arrangement_6_rise_phase(self):
        """
        패턴 6: 단기 > 장기 > 중기
        상승 변화기2, 단기선이 장기선 위로
        """
        df = pd.DataFrame({
            'EMA_5': [105, 106, 107],
            'EMA_20': [90, 91, 92],
            'EMA_40': [100, 101, 102]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        assert all(arrangement == 6), "모든 시점이 패턴 6이어야 함"
    
    def test_arrangement_edge_cases(self):
        """
        엣지 케이스: NaN, 동일값 등
        """
        # NaN 포함
        df = pd.DataFrame({
            'EMA_5': [np.nan, 110, 120],
            'EMA_20': [105, np.nan, 112],
            'EMA_40': [100, 102, np.nan]
        })
        
        arrangement = determine_ma_arrangement(df)
        
        # NaN이 있는 행은 0 (판단 불가)
        assert arrangement.iloc[0] == 0, "NaN이 있으면 판단 불가"
        assert arrangement.iloc[1] == 0, "NaN이 있으면 판단 불가"
        assert arrangement.iloc[2] == 0, "NaN이 있으면 판단 불가"
    
    def test_arrangement_missing_columns(self):
        """
        필수 컬럼 누락 시 에러
        """
        df = pd.DataFrame({
            'EMA_5': [110, 115, 120],
            'EMA_20': [105, 108, 112]
            # EMA_40 누락
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            determine_ma_arrangement(df)
    
    def test_arrangement_invalid_type(self):
        """
        잘못된 타입 입력 시 에러
        """
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            determine_ma_arrangement([1, 2, 3])


class TestDetectMACDZeroCross:
    """MACD 0선 교차 감지 테스트"""
    
    def test_golden_cross_upper(self):
        """
        MACD(상) 골든크로스 감지
        음수 → 양수 전환
        """
        df = pd.DataFrame({
            'MACD_상': [-1.0, -0.5, 0.5, 1.0],
            'MACD_중': [0.0, 0.0, 0.0, 0.0],
            'MACD_하': [0.0, 0.0, 0.0, 0.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_상'].iloc[0] == 0, "첫 행은 비교 불가"
        assert crosses['Cross_상'].iloc[1] == 0, "아직 교차 없음"
        assert crosses['Cross_상'].iloc[2] == 1, "골든크로스 발생"
        assert crosses['Cross_상'].iloc[3] == 0, "이미 양수"
    
    def test_golden_cross_middle(self):
        """
        MACD(중) 골든크로스 감지
        """
        df = pd.DataFrame({
            'MACD_상': [0.0, 0.0, 0.0, 0.0],
            'MACD_중': [-2.0, -1.0, 0.5, 1.5],
            'MACD_하': [0.0, 0.0, 0.0, 0.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_중'].iloc[2] == 1, "골든크로스 발생"
    
    def test_golden_cross_lower(self):
        """
        MACD(하) 골든크로스 감지
        """
        df = pd.DataFrame({
            'MACD_상': [0.0, 0.0, 0.0, 0.0],
            'MACD_중': [0.0, 0.0, 0.0, 0.0],
            'MACD_하': [-3.0, -1.5, 0.2, 1.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_하'].iloc[2] == 1, "골든크로스 발생"
    
    def test_dead_cross_upper(self):
        """
        MACD(상) 데드크로스 감지
        양수 → 음수 전환
        """
        df = pd.DataFrame({
            'MACD_상': [1.0, 0.5, -0.5, -1.0],
            'MACD_중': [0.0, 0.0, 0.0, 0.0],
            'MACD_하': [0.0, 0.0, 0.0, 0.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_상'].iloc[0] == 0, "첫 행은 비교 불가"
        assert crosses['Cross_상'].iloc[1] == 0, "아직 교차 없음"
        assert crosses['Cross_상'].iloc[2] == -1, "데드크로스 발생"
        assert crosses['Cross_상'].iloc[3] == 0, "이미 음수"
    
    def test_dead_cross_middle(self):
        """
        MACD(중) 데드크로스 감지
        """
        df = pd.DataFrame({
            'MACD_상': [0.0, 0.0, 0.0, 0.0],
            'MACD_중': [2.0, 1.0, -0.5, -1.5],
            'MACD_하': [0.0, 0.0, 0.0, 0.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_중'].iloc[2] == -1, "데드크로스 발생"
    
    def test_dead_cross_lower(self):
        """
        MACD(하) 데드크로스 감지
        """
        df = pd.DataFrame({
            'MACD_상': [0.0, 0.0, 0.0, 0.0],
            'MACD_중': [0.0, 0.0, 0.0, 0.0],
            'MACD_하': [3.0, 1.5, -0.2, -1.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        assert crosses['Cross_하'].iloc[2] == -1, "데드크로스 발생"
    
    def test_multiple_crosses(self):
        """
        여러 MACD에서 동시에 교차 발생
        """
        df = pd.DataFrame({
            'MACD_상': [-1.0, 0.5, 1.0],
            'MACD_중': [1.0, -0.5, -1.0],
            'MACD_하': [-0.5, 0.3, 0.8]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        # 2번째 행에서 3개 MACD 모두 교차
        assert crosses['Cross_상'].iloc[1] == 1, "MACD(상) 골든크로스"
        assert crosses['Cross_중'].iloc[1] == -1, "MACD(중) 데드크로스"
        assert crosses['Cross_하'].iloc[1] == 1, "MACD(하) 골든크로스"
    
    def test_zero_line_oscillation(self):
        """
        0선 근처에서 진동하는 경우
        """
        df = pd.DataFrame({
            'MACD_상': [0.1, -0.1, 0.1, -0.1, 0.1],
            'MACD_중': [0.0, 0.0, 0.0, 0.0, 0.0],
            'MACD_하': [0.0, 0.0, 0.0, 0.0, 0.0]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        # 여러 번 교차 발생
        assert crosses['Cross_상'].iloc[1] == -1, "첫 데드크로스"
        assert crosses['Cross_상'].iloc[2] == 1, "첫 골든크로스"
        assert crosses['Cross_상'].iloc[3] == -1, "두 번째 데드크로스"
        assert crosses['Cross_상'].iloc[4] == 1, "두 번째 골든크로스"
    
    def test_macd_missing_columns(self):
        """
        필수 컬럼 누락 시 에러
        """
        df = pd.DataFrame({
            'MACD_상': [1.0, 0.5, -0.5],
            'MACD_중': [0.0, 0.0, 0.0]
            # MACD_하 누락
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            detect_macd_zero_cross(df)
    
    def test_macd_invalid_type(self):
        """
        잘못된 타입 입력 시 에러
        """
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            detect_macd_zero_cross([1, 2, 3])
    
    def test_cross_with_nan(self):
        """
        NaN이 포함된 경우
        """
        df = pd.DataFrame({
            'MACD_상': [np.nan, -1.0, 0.5, 1.0],
            'MACD_중': [1.0, np.nan, -0.5, -1.0],
            'MACD_하': [-0.5, 0.3, np.nan, 0.8]
        })
        
        crosses = detect_macd_zero_cross(df)
        
        # NaN이 있는 교차는 False로 처리됨
        assert crosses['Cross_상'].iloc[1] == 0, "이전 값이 NaN이면 교차 감지 안됨"
        assert crosses['Cross_중'].iloc[2] == 0, "현재 값이 NaN이면 교차 감지 안됨"

class TestDetermineStage:
    """스테이지 판단 테스트"""

    def test_stage_1_determination(self):
        """제1스테이지: 완전 정배열 + MACD(하) 골든크로스"""
        df = pd.DataFrame({
            'EMA_5': [110, 115, 120],
            'EMA_20': [105, 108, 112],
            'EMA_40': [100, 102, 105],
            'MACD_상': [1.0, 1.2, 1.5],
            'MACD_중': [0.5, 0.8, 1.0],
            'MACD_하': [-0.5, 0.2, 0.8]  # 골든크로스
        })

        stage = determine_stage(df)

        # MACD(하) 골든크로스 발생 → 제1스테이지 확정
        assert stage.iloc[1] == 1, "골든크로스3 발생으로 제1스테이지 확정"

    def test_stage_2_determination(self):
        """제2스테이지: 패턴2 + MACD(상) 데드크로스"""
        df = pd.DataFrame({
            'EMA_5': [105, 104, 103],
            'EMA_20': [108, 107, 106],
            'EMA_40': [100, 101, 102],
            'MACD_상': [0.5, 0.1, -0.2],  # 데드크로스
            'MACD_중': [0.8, 0.9, 1.0],
            'MACD_하': [1.0, 1.1, 1.2]
        })

        stage = determine_stage(df)

        # MACD(상) 데드크로스 발생 → 제2스테이지 확정
        assert stage.iloc[2] == 2, "데드크로스1 발생으로 제2스테이지 확정"

    def test_stage_3_determination(self):
        """제3스테이지: 패턴3 + MACD(중) 데드크로스"""
        df = pd.DataFrame({
            'EMA_5': [95, 94, 93],
            'EMA_20': [108, 107, 106],
            'EMA_40': [100, 101, 102],
            'MACD_상': [-0.5, -0.8, -1.0],
            'MACD_중': [0.5, 0.1, -0.3],  # 데드크로스
            'MACD_하': [1.0, 0.9, 0.8]
        })

        stage = determine_stage(df)

        # MACD(중) 데드크로스 발생 → 제3스테이지 확정
        assert stage.iloc[2] == 3, "데드크로스2 발생으로 제3스테이지 확정"

    def test_stage_4_determination(self):
        """제4스테이지: 완전 역배열 + MACD(하) 데드크로스"""
        df = pd.DataFrame({
            'EMA_5': [90, 85, 80],
            'EMA_20': [95, 92, 88],
            'EMA_40': [100, 98, 95],
            'MACD_상': [-1.0, -1.2, -1.5],
            'MACD_중': [-0.5, -0.8, -1.0],
            'MACD_하': [0.5, 0.1, -0.3]  # 데드크로스
        })

        stage = determine_stage(df)

        # MACD(하) 데드크로스 발생 → 제4스테이지 확정
        assert stage.iloc[2] == 4, "데드크로스3 발생으로 제4스테이지 확정"

    def test_stage_5_determination(self):
        """제5스테이지: 패턴5 + MACD(상) 골든크로스"""
        df = pd.DataFrame({
            'EMA_5': [95, 96, 97],
            'EMA_20': [92, 93, 94],
            'EMA_40': [100, 101, 102],
            'MACD_상': [-0.5, -0.1, 0.3],  # 골든크로스
            'MACD_중': [-0.8, -0.9, -1.0],
            'MACD_하': [-1.0, -1.1, -1.2]
        })

        stage = determine_stage(df)

        # MACD(상) 골든크로스 발생 → 제5스테이지 확정
        assert stage.iloc[2] == 5, "골든크로스1 발생으로 제5스테이지 확정"

    def test_stage_6_determination(self):
        """제6스테이지: 패턴6 + MACD(중) 골든크로스"""
        df = pd.DataFrame({
            'EMA_5': [105, 107, 110],
            'EMA_20': [92, 93, 94],
            'EMA_40': [100, 101, 102],
            'MACD_상': [0.5, 0.8, 1.0],
            'MACD_중': [-0.5, -0.1, 0.3],  # 골든크로스
            'MACD_하': [-1.0, -0.9, -0.8]
        })

        stage = determine_stage(df)

        # MACD(중) 골든크로스 발생 → 제6스테이지 확정
        assert stage.iloc[2] == 6, "골든크로스2 발생으로 제6스테이지 확정"

    def test_stage_transition_scenario(self):
        """제1→제2→제3 전환 시나리오"""
        df = pd.DataFrame({
            # 날짜 0: 제1스테이지 (완전 정배열)
            'EMA_5': [110, 108, 105],
            'EMA_20': [105, 107, 108],
            'EMA_40': [100, 102, 110],
            'MACD_상': [1.0, 0.5, -0.3],  # 데드크로스
            'MACD_중': [1.5, 1.2, 0.5],
            'MACD_하': [2.0, 1.8, 1.5]
        })

        stage = determine_stage(df)

        # 배열 기반 초기 판단
        assert stage.iloc[0] == 1, "완전 정배열 → 제1스테이지"

        # MACD(상) 데드크로스 → 제2스테이지
        assert stage.iloc[2] == 2, "데드크로스1 발생 → 제2스테이지"

    def test_stage_missing_columns(self):
        """에러: 필수 컬럼 누락"""
        df = pd.DataFrame({
            'EMA_5': [110, 115],
            'EMA_20': [105, 108],
            'EMA_40': [100, 102]
            # MACD 컬럼 누락
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            determine_stage(df)


class TestDetectStageTransition:
    """스테이지 전환 감지 테스트"""

    def test_transition_detection(self):
        """정상적인 스테이지 전환 감지"""
        df = pd.DataFrame({
            'Stage': [1, 1, 2, 2, 3, 3]
        })

        transition = detect_stage_transition(df)

        assert transition.iloc[0] == 0, "첫 행은 비교 불가"
        assert transition.iloc[1] == 0, "1→1 (유지)"
        assert transition.iloc[2] == 12, "1→2 전환"
        assert transition.iloc[3] == 0, "2→2 (유지)"
        assert transition.iloc[4] == 23, "2→3 전환"
        assert transition.iloc[5] == 0, "3→3 (유지)"

    def test_no_transition(self):
        """스테이지 전환이 없는 경우"""
        df = pd.DataFrame({
            'Stage': [1, 1, 1, 1, 1]
        })

        transition = detect_stage_transition(df)

        assert all(transition == 0), "모든 값이 0이어야 함"

    def test_multiple_transitions(self):
        """연속적인 스테이지 전환"""
        df = pd.DataFrame({
            'Stage': [1, 2, 3, 4, 5, 6, 1]
        })

        transition = detect_stage_transition(df)

        assert transition.iloc[0] == 0, "첫 행"
        assert transition.iloc[1] == 12, "1→2"
        assert transition.iloc[2] == 23, "2→3"
        assert transition.iloc[3] == 34, "3→4"
        assert transition.iloc[4] == 45, "4→5"
        assert transition.iloc[5] == 56, "5→6"
        assert transition.iloc[6] == 61, "6→1 (순환)"

    def test_transition_encoding(self):
        """비순차 전환도 올바르게 인코딩"""
        df = pd.DataFrame({
            'Stage': [1, 3, 2, 5]  # 비정상 패턴
        })

        transition = detect_stage_transition(df)

        assert transition.iloc[0] == 0, "첫 행"
        assert transition.iloc[1] == 13, "1→3"
        assert transition.iloc[2] == 32, "3→2"
        assert transition.iloc[3] == 25, "2→5"

    def test_transition_missing_column(self):
        """에러: Stage 컬럼 누락"""
        df = pd.DataFrame({
            'NotStage': [1, 2, 3]
        })

        with pytest.raises(ValueError, match="Stage 컬럼이 필요합니다"):
            detect_stage_transition(df)

    def test_transition_invalid_type(self):
        """에러: 잘못된 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            detect_stage_transition([1, 2, 3])

class TestCalculateMaSpread:
    """calculate_ma_spread() 함수 테스트"""

    def test_spread_calculation(self):
        """간격 계산 정확성"""
        df = pd.DataFrame({
            'EMA_5': [110, 115, 120],
            'EMA_20': [105, 108, 112],
            'EMA_40': [100, 102, 105]
        })

        spreads = calculate_ma_spread(df)

        # Spread_5_20 확인
        assert spreads['Spread_5_20'].iloc[0] == 5  # 110 - 105
        assert spreads['Spread_5_20'].iloc[1] == 7  # 115 - 108
        assert spreads['Spread_5_20'].iloc[2] == 8  # 120 - 112

        # Spread_20_40 확인
        assert spreads['Spread_20_40'].iloc[0] == 5  # 105 - 100

        # Spread_5_40 확인
        assert spreads['Spread_5_40'].iloc[0] == 10  # 110 - 100

        # 3개 컬럼 존재
        assert len(spreads.columns) == 3

    def test_spread_positive_negative(self):
        """양수(정배열)/음수(역배열) 간격"""
        df = pd.DataFrame({
            'EMA_5': [110, 95],  # 정배열 → 역배열
            'EMA_20': [105, 100],
            'EMA_40': [100, 105]
        })

        spreads = calculate_ma_spread(df)

        # 첫 행: 정배열 (양수)
        assert spreads['Spread_5_20'].iloc[0] > 0
        assert spreads['Spread_20_40'].iloc[0] > 0
        assert spreads['Spread_5_40'].iloc[0] > 0

        # 둘째 행: 역배열 (음수)
        assert spreads['Spread_5_20'].iloc[1] < 0
        assert spreads['Spread_20_40'].iloc[1] < 0
        assert spreads['Spread_5_40'].iloc[1] < 0

    def test_spread_change_tracking(self):
        """간격 확대/축소 추적"""
        df = pd.DataFrame({
            'EMA_5': [110, 112, 115],  # 간격 확대
            'EMA_20': [105, 106, 107],
            'EMA_40': [100, 101, 102]
        })

        spreads = calculate_ma_spread(df)

        # Spread_5_20 확대 확인
        assert spreads['Spread_5_20'].iloc[0] == 5
        assert spreads['Spread_5_20'].iloc[1] == 6
        assert spreads['Spread_5_20'].iloc[2] == 8

        # 간격이 계속 확대됨
        assert spreads['Spread_5_20'].is_monotonic_increasing

    def test_spread_with_nan(self):
        """NaN 포함 시 전파"""
        df = pd.DataFrame({
            'EMA_5': [110, np.nan, 120],
            'EMA_20': [105, 108, 112],
            'EMA_40': [100, 102, 105]
        })

        spreads = calculate_ma_spread(df)

        # NaN은 전파됨
        assert not pd.isna(spreads['Spread_5_20'].iloc[0])
        assert pd.isna(spreads['Spread_5_20'].iloc[1])
        assert not pd.isna(spreads['Spread_5_20'].iloc[2])

    def test_spread_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({
            'EMA_5': [110, 115],
            'EMA_20': [105, 108]
            # EMA_40 누락
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            calculate_ma_spread(df)

    def test_spread_invalid_type(self):
        """잘못된 타입"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            calculate_ma_spread([1, 2, 3])


class TestCheckMaSlope:
    """check_ma_slope() 함수 테스트"""

    def test_slope_uptrend(self):
        """우상향 기울기 판단"""
        df = pd.DataFrame({
            'EMA_5': [100, 102, 105, 109, 114],  # 증가
            'EMA_20': [95, 97, 99, 102, 105],
            'EMA_40': [90, 91, 93, 95, 97]
        })

        slopes = check_ma_slope(df, period=3)

        # 모든 기울기가 양수
        assert slopes['Slope_EMA_5'].iloc[-1] > 0
        assert slopes['Slope_EMA_20'].iloc[-1] > 0
        assert slopes['Slope_EMA_40'].iloc[-1] > 0

        # 3개 컬럼 존재
        assert len(slopes.columns) == 3

    def test_slope_downtrend(self):
        """우하향 기울기 판단"""
        df = pd.DataFrame({
            'EMA_5': [114, 109, 105, 102, 100],  # 감소
            'EMA_20': [105, 102, 99, 97, 95],
            'EMA_40': [97, 95, 93, 91, 90]
        })

        slopes = check_ma_slope(df, period=3)

        # 모든 기울기가 음수
        assert slopes['Slope_EMA_5'].iloc[-1] < 0
        assert slopes['Slope_EMA_20'].iloc[-1] < 0
        assert slopes['Slope_EMA_40'].iloc[-1] < 0

    def test_slope_flat(self):
        """평행 기울기 판단"""
        df = pd.DataFrame({
            'EMA_5': [100, 100.1, 99.9, 100.2, 100],  # 거의 변화 없음
            'EMA_20': [95, 95.1, 94.9, 95.1, 95],
            'EMA_40': [90, 90.05, 89.95, 90.1, 90]
        })

        slopes = check_ma_slope(df, period=3)

        # 기울기가 0에 가까움
        assert abs(slopes['Slope_EMA_5'].iloc[-1]) < 0.1
        assert abs(slopes['Slope_EMA_20'].iloc[-1]) < 0.1
        assert abs(slopes['Slope_EMA_40'].iloc[-1]) < 0.1

    def test_slope_custom_period(self):
        """커스텀 period 테스트"""
        # 비선형 데이터 사용 (가속하는 패턴)
        df = pd.DataFrame({
            'EMA_5': [100, 101, 103, 106, 110, 115, 121, 128, 136, 145],   # 가속 증가
            'EMA_20': [95, 96, 97, 99, 101, 104, 107, 111, 116, 122],     # 가속 증가
            'EMA_40': [90, 91, 92, 93, 95, 97, 99, 102, 105, 109]         # 가속 증가
        })


        # period=3과 period=5 비교
        slopes_3 = check_ma_slope(df, period=3)
        slopes_5 = check_ma_slope(df, period=5)

        # 둘 다 양수이지만 값은 다름
        assert slopes_3['Slope_EMA_5'].iloc[-1] > 0
        assert slopes_5['Slope_EMA_5'].iloc[-1] > 0
        assert slopes_3['Slope_EMA_5'].iloc[-1] != slopes_5['Slope_EMA_5'].iloc[-1]

    def test_slope_invalid_period(self):
        """잘못된 period"""
        df = pd.DataFrame({
            'EMA_5': [100, 102],
            'EMA_20': [95, 97],
            'EMA_40': [90, 91]
        })

        with pytest.raises(ValueError, match="period는 2 이상"):
            check_ma_slope(df, period=1)

    def test_slope_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({
            'EMA_5': [100, 102],
            'EMA_20': [95, 97]
            # EMA_40 누락
        })

        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            check_ma_slope(df, period=3)


class TestGetStageStrategy:
    """get_stage_strategy() 함수 테스트"""

    def test_strategy_stage_1(self):
        """제1스테이지 전략"""
        strategy = get_stage_strategy(1)

        assert strategy['stage'] == 1
        assert strategy['name'] == '안정 상승기'
        assert strategy['market_phase'] == '강세장'
        assert strategy['action'] == 'buy'
        assert strategy['risk_level'] == 'low'
        assert len(strategy['key_points']) == 5
        assert 'description' in strategy

    def test_strategy_stage_2(self):
        """제2스테이지 전략"""
        strategy = get_stage_strategy(2)

        assert strategy['stage'] == 2
        assert strategy['name'] == '하락 변화기1'
        assert strategy['action'] == 'hold_or_exit'
        assert strategy['risk_level'] == 'medium'

    def test_strategy_stage_3(self):
        """제3스테이지 전략"""
        strategy = get_stage_strategy(3)

        assert strategy['stage'] == 3
        assert strategy['name'] == '하락 변화기2'
        assert strategy['action'] == 'sell_or_short'
        assert strategy['risk_level'] == 'high'

    def test_strategy_stage_4(self):
        """제4스테이지 전략"""
        strategy = get_stage_strategy(4)

        assert strategy['stage'] == 4
        assert strategy['name'] == '안정 하락기'
        assert strategy['action'] == 'short_or_wait'
        assert strategy['risk_level'] == 'low'

    def test_strategy_stage_5(self):
        """제5스테이지 전략"""
        strategy = get_stage_strategy(5)

        assert strategy['stage'] == 5
        assert strategy['name'] == '상승 변화기1'
        assert strategy['action'] == 'hold_or_exit'
        assert strategy['risk_level'] == 'medium'

    def test_strategy_stage_6(self):
        """제6스테이지 전략"""
        strategy = get_stage_strategy(6)

        assert strategy['stage'] == 6
        assert strategy['name'] == '상승 변화기2'
        assert strategy['action'] == 'cover_or_buy'
        assert strategy['risk_level'] == 'high'

    def test_strategy_with_macd_directions(self):
        """MACD 방향 정보 포함"""
        macd_dirs = {'상': 'up', '중': 'up', '하': 'up'}

        strategy = get_stage_strategy(1, macd_directions=macd_dirs)

        # MACD 방향 정보 확인
        assert 'macd_directions' in strategy
        assert strategy['macd_directions'] == macd_dirs

        # MACD 일치도 확인
        assert 'macd_alignment' in strategy
        alignment = strategy['macd_alignment']
        assert alignment['up_count'] == 3
        assert alignment['down_count'] == 0
        assert alignment['neutral_count'] == 0
        assert alignment['strength'] == 'strong'

    def test_strategy_with_weak_macd_alignment(self):
        """약한 MACD 일치도"""
        macd_dirs = {'상': 'up', '중': 'down', '하': 'neutral'}

        strategy = get_stage_strategy(1, macd_directions=macd_dirs)

        alignment = strategy['macd_alignment']
        assert alignment['up_count'] == 1
        assert alignment['down_count'] == 1
        assert alignment['neutral_count'] == 1
        assert alignment['strength'] == 'weak'

    def test_strategy_invalid_stage_type(self):
        """잘못된 스테이지 타입"""
        with pytest.raises(TypeError, match="stage는 정수여야 합니다"):
            get_stage_strategy("1")

    def test_strategy_invalid_stage_range(self):
        """잘못된 스테이지 범위"""
        with pytest.raises(ValueError, match="stage는 1~6 사이여야 합니다"):
            get_stage_strategy(0)

        with pytest.raises(ValueError, match="stage는 1~6 사이여야 합니다"):
            get_stage_strategy(7)
