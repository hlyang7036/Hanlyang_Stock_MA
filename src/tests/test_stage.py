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
    detect_stage_transition
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