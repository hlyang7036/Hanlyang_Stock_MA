"""
Level 4-2 청산 신호 생성 테스트

이 모듈은 청산 신호 생성 함수들을 테스트합니다.

Test Classes:
    TestCheckHistogramPeakout: check_histogram_peakout() 함수 테스트
    TestCheckMacdPeakout: check_macd_peakout() 함수 테스트
    TestCheckMacdCross: check_macd_cross() 함수 테스트
    TestGenerateExitSignal: generate_exit_signal() 함수 테스트
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.signal.exit import (
    generate_exit_signal,
    check_histogram_peakout,
    check_macd_peakout,
    check_macd_cross
)


class TestCheckHistogramPeakout:
    """check_histogram_peakout() 함수 테스트"""
    
    def test_long_histogram_peakout(self):
        """매수 포지션 히스토그램 피크아웃"""
        df = pd.DataFrame({
            'Histogram': [1.0, 2.0, 3.0, 2.5, 2.0]  # 고점 후 하락
        })
        
        result = check_histogram_peakout(df, 'long')
        
        # 3.0에서 고점 후 하락 시작
        assert result.iloc[3] == True  # 피크아웃 발생
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == False
    
    def test_short_histogram_peakout(self):
        """매도 포지션 히스토그램 피크아웃"""
        df = pd.DataFrame({
            'Histogram': [-1.0, -2.0, -3.0, -2.5, -2.0]  # 저점 후 상승
        })
        
        result = check_histogram_peakout(df, 'short')
        
        # -3.0에서 저점 후 상승 시작
        assert result.iloc[3] == True  # 피크아웃 발생
    
    def test_no_histogram_peakout(self):
        """히스토그램 피크아웃 없음"""
        df = pd.DataFrame({
            'Histogram': [1.0, 1.5, 2.0, 2.5, 3.0]  # 계속 상승
        })
        
        result = check_histogram_peakout(df, 'long')
        
        # 피크아웃 없음
        assert result.sum() == 0
    
    def test_histogram_peakout_invalid_position_type(self):
        """잘못된 position_type"""
        df = pd.DataFrame({'Histogram': [1.0, 2.0, 1.5]})
        
        with pytest.raises(ValueError, match="'long' 또는 'short'"):
            check_histogram_peakout(df, 'invalid')
    
    def test_histogram_peakout_missing_column(self):
        """Histogram 컬럼 누락"""
        df = pd.DataFrame({'MACD': [1.0, 2.0, 1.5]})
        
        with pytest.raises(ValueError, match="Histogram 컬럼이 필요"):
            check_histogram_peakout(df, 'long')


class TestCheckMacdPeakout:
    """check_macd_peakout() 함수 테스트"""
    
    def test_long_macd_peakout(self):
        """매수 포지션 MACD 피크아웃"""
        df = pd.DataFrame({
            'MACD': [1.0, 2.0, 3.0, 2.5, 2.0]  # 고점 후 하락
        })
        
        result = check_macd_peakout(df, 'long')
        
        # 피크아웃 발생
        assert result.iloc[3] == True
    
    def test_short_macd_peakout(self):
        """매도 포지션 MACD 피크아웃"""
        df = pd.DataFrame({
            'MACD': [-1.0, -2.0, -3.0, -2.5, -2.0]  # 저점 후 상승
        })
        
        result = check_macd_peakout(df, 'short')
        
        # 피크아웃 발생
        assert result.iloc[3] == True
    
    def test_custom_macd_column(self):
        """커스텀 MACD 컬럼"""
        df = pd.DataFrame({
            'MACD_Custom': [1.0, 2.0, 3.0, 2.5, 2.0]
        })
        
        result = check_macd_peakout(df, 'long', macd_column='MACD_Custom')
        
        assert result.iloc[3] == True
    
    def test_macd_peakout_missing_column(self):
        """MACD 컬럼 누락"""
        df = pd.DataFrame({'Histogram': [1.0, 2.0, 1.5]})
        
        with pytest.raises(ValueError, match="MACD 컬럼이 필요"):
            check_macd_peakout(df, 'long')


class TestCheckMacdCross:
    """check_macd_cross() 함수 테스트"""
    
    def test_long_dead_cross(self):
        """매수 포지션 데드크로스"""
        df = pd.DataFrame({
            'MACD': [2.0, 1.5, 1.0, 0.5],    # 하락
            'Signal': [1.0, 1.0, 1.0, 1.0]   # 유지
        })
        
        result = check_macd_cross(df, 'long')
        
        # MACD가 Signal 위→아래로 교차
        assert result.iloc[0] == False  # 첫 행은 비교 불가
        assert result.iloc[1] == False  # 아직 위
        assert result.iloc[2] == True   # 데드크로스 발생
    
    def test_short_golden_cross(self):
        """매도 포지션 골든크로스"""
        df = pd.DataFrame({
            'MACD': [0.5, 1.0, 1.5, 2.0],    # 상승
            'Signal': [1.0, 1.0, 1.0, 1.0]   # 유지
        })
        
        result = check_macd_cross(df, 'short')
        
        # MACD가 Signal 아래→위로 교차
        assert result.iloc[0] == False  # 첫 행은 비교 불가
        assert result.iloc[1] == False  # 아직 아래
        assert result.iloc[2] == True   # 골든크로스 발생
    
    def test_no_cross(self):
        """교차 없음"""
        df = pd.DataFrame({
            'MACD': [2.0, 2.5, 3.0, 3.5],    # 계속 위
            'Signal': [1.0, 1.0, 1.0, 1.0]
        })
        
        result = check_macd_cross(df, 'long')
        
        # 교차 없음
        assert result.sum() == 0
    
    def test_custom_columns(self):
        """커스텀 컬럼명"""
        df = pd.DataFrame({
            'MACD_Line': [2.0, 1.5, 1.0, 0.5],
            'Signal_Line': [1.0, 1.0, 1.0, 1.0]
        })
        
        result = check_macd_cross(
            df, 'long',
            macd_column='MACD_Line',
            signal_column='Signal_Line'
        )
        
        assert result.iloc[2] == True
    
    def test_macd_cross_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({
            'MACD': [1.0, 2.0, 1.5]
            # Signal 누락
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            check_macd_cross(df, 'long')


class TestGenerateExitSignal:
    """generate_exit_signal() 함수 테스트"""
    
    def test_exit_level_1_histogram(self):
        """레벨 1: 히스토그램 피크아웃"""
        df = pd.DataFrame({
            'Histogram': [1.0, 2.0, 3.0, 2.5, 2.0],  # 피크아웃
            'MACD': [1.0, 1.5, 2.0, 2.5, 3.0],       # 상승 중
            'Signal': [0.5, 0.5, 0.5, 0.5, 0.5]
        })
        
        result = generate_exit_signal(df, 'long')
        
        # 레벨 1 신호 발생
        assert result['Exit_Level'].iloc[3] == 1
        assert result['Exit_Percentage'].iloc[3] == 0
        assert result['Should_Exit'].iloc[3] == False  # 경계만
        assert '히스토그램' in result['Exit_Reason'].iloc[3]
    
    def test_exit_level_2_macd(self):
        """레벨 2: MACD선 피크아웃"""
        df = pd.DataFrame({
            'Histogram': [1.0, 1.0, 1.0, 1.0, 1.0],  # 변화 없음
            'MACD': [1.0, 2.0, 3.0, 2.5, 2.0],       # 피크아웃
            'Signal': [0.5, 0.5, 0.5, 0.5, 0.5]
        })
        
        result = generate_exit_signal(df, 'long')
        
        # 레벨 2 신호 발생
        assert result['Exit_Level'].iloc[3] == 2
        assert result['Exit_Percentage'].iloc[3] == 50
        assert result['Should_Exit'].iloc[3] == True  # 50% 청산
        assert 'MACD선' in result['Exit_Reason'].iloc[3]
    
    def test_exit_level_3_cross(self):
        """레벨 3: MACD-시그널 교차"""
        df = pd.DataFrame({
            'Histogram': [1.0, 1.0, 1.0, 1.0],
            'MACD': [2.0, 1.5, 1.0, 0.5],        # 하락
            'Signal': [1.0, 1.0, 1.0, 1.0]
        })
        
        result = generate_exit_signal(df, 'long')
        
        # 레벨 3 신호 발생
        assert result['Exit_Level'].iloc[2] == 3
        assert result['Exit_Percentage'].iloc[2] == 100
        assert result['Should_Exit'].iloc[2] == True  # 100% 청산
        assert '데드크로스' in result['Exit_Reason'].iloc[2]
    
    def test_exit_signal_priority(self):
        """신호 우선순위 (레벨 3 > 2 > 1)"""
        df = pd.DataFrame({
            'Histogram': [0.5, 1.0, 2.0, 1.5, 1.0, 0.8],  # 레벨 1 (인덱스 3)
            'MACD': [1.0, 2.0, 3.0, 2.5, 1.0, 0.5],       # 레벨 2 (인덱스 3), 레벨 3 (인덱스 4)
            'Signal': [1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
        })
        
        result = generate_exit_signal(df, 'long')
        
        # 동시 발생 시 최고 레벨 우선
        assert result['Exit_Level'].iloc[3] == 2  # 레벨 2 우선
        assert result['Exit_Level'].iloc[4] == 3  # 레벨 3 최우선
    
    def test_short_position_exit(self):
        """매도 포지션 청산 신호"""
        df = pd.DataFrame({
            'Histogram': [-1.0, -2.0, -1.5, -1.0],  # 상승 피크아웃
            'MACD': [0.5, 1.0, 1.5, 2.0],           # 상승 (골든크로스)
            'Signal': [1.0, 1.0, 1.0, 1.0]
        })
        
        result = generate_exit_signal(df, 'short')
        
        # 골든크로스 발생
        assert result['Exit_Level'].iloc[2] == 3
        assert '골든크로스' in result['Exit_Reason'].iloc[2]
    
    def test_no_exit_signal(self):
        """청산 신호 없음"""
        df = pd.DataFrame({
            'Histogram': [1.0, 1.5, 2.0, 2.5],  # 계속 상승
            'MACD': [1.0, 1.5, 2.0, 2.5],       # 계속 상승
            'Signal': [0.5, 0.5, 0.5, 0.5]
        })
        
        result = generate_exit_signal(df, 'long')
        
        # 모든 레벨 0
        assert (result['Exit_Level'] == 0).all()
        assert (result['Should_Exit'] == False).all()
    
    def test_exit_signal_invalid_input(self):
        """잘못된 입력"""
        with pytest.raises(TypeError, match="DataFrame이 필요"):
            generate_exit_signal([1, 2, 3], 'long')
    
    def test_exit_signal_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({
            'MACD': [1.0, 2.0, 1.5]
            # Histogram, Signal 누락
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            generate_exit_signal(df, 'long')
