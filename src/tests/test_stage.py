"""
스테이지 분석 모듈 테스트

Stage 분석 모듈의 함수들을 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.stage import (
    determine_ma_arrangement,
    detect_macd_zero_cross,
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
