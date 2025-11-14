"""
Level 4-1 진입 신호 생성 테스트

이 모듈은 진입 신호 생성 함수들을 테스트합니다.

Test Classes:
    TestGenerateBuySignal: generate_buy_signal() 함수 테스트
    TestGenerateSellSignal: generate_sell_signal() 함수 테스트
    TestCheckEntryConditions: check_entry_conditions() 함수 테스트
    TestGenerateEntrySignals: generate_entry_signals() 함수 테스트
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.signal.entry import (
    generate_buy_signal,
    generate_sell_signal,
    check_entry_conditions,
    generate_entry_signals
)


class TestGenerateBuySignal:
    """generate_buy_signal() 함수 테스트"""
    
    def test_normal_buy_signal(self):
        """통상 매수 신호 생성"""
        df = pd.DataFrame({
            'Stage': [5, 6, 6, 1],
            'Dir_MACD_상': ['up', 'up', 'up', 'up'],
            'Dir_MACD_중': ['up', 'up', 'down', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up', 'up'],
            'Close': [50000, 51000, 52000, 53000]
        })
        
        result = generate_buy_signal(df, 'normal')
        
        # 제6스테이지 + 3개 MACD 상승 = 신호 발생
        assert result['Buy_Signal'].iloc[1] == 1  # 조건 충족
        assert result['Buy_Signal'].iloc[0] == 0  # 제5스테이지 (통상 매수 X)
        assert result['Buy_Signal'].iloc[2] == 0  # MACD 중 하락
        assert result['Buy_Signal'].iloc[3] == 0  # 제1스테이지
        
        # 신호 발생 이유
        assert '통상 매수' in result['Signal_Reason'].iloc[1]
    
    def test_early_buy_signal(self):
        """조기 매수 신호 생성"""
        df = pd.DataFrame({
            'Stage': [4, 5, 5, 6],
            'Dir_MACD_상': ['up', 'up', 'down', 'up'],
            'Dir_MACD_중': ['up', 'up', 'up', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up', 'up'],
            'Close': [48000, 49000, 50000, 51000]
        })
        
        result = generate_buy_signal(df, 'early')
        
        # 제5스테이지 + 3개 MACD 상승 = 조기 매수 신호
        assert result['Buy_Signal'].iloc[1] == 2  # 조건 충족
        assert result['Buy_Signal'].iloc[0] == 0  # 제4스테이지
        assert result['Buy_Signal'].iloc[2] == 0  # MACD 상 하락
        assert result['Buy_Signal'].iloc[3] == 0  # 제6스테이지 (조기 매수 X)
        
        # 신호 발생 이유
        assert '조기 매수' in result['Signal_Reason'].iloc[1]
    
    def test_no_buy_signal(self):
        """매수 신호 없음"""
        df = pd.DataFrame({
            'Stage': [1, 2, 3, 4],
            'Dir_MACD_상': ['up', 'down', 'down', 'down'],
            'Dir_MACD_중': ['up', 'down', 'down', 'down'],
            'Dir_MACD_하': ['up', 'down', 'down', 'down'],
            'Close': [50000, 49000, 48000, 47000]
        })
        
        result = generate_buy_signal(df, 'normal')
        
        # 모든 행에서 신호 없음
        assert (result['Buy_Signal'] == 0).all()
    
    def test_buy_signal_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({
            'Stage': [6, 6],
            'Dir_MACD_상': ['up', 'up']
            # Dir_MACD_중, Dir_MACD_하, Close 누락
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            generate_buy_signal(df, 'normal')
    
    def test_buy_signal_invalid_type(self):
        """잘못된 signal_type"""
        df = pd.DataFrame({
            'Stage': [6],
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['up'],
            'Dir_MACD_하': ['up'],
            'Close': [50000]
        })
        
        with pytest.raises(ValueError, match="'normal' 또는 'early'"):
            generate_buy_signal(df, 'invalid')


class TestGenerateSellSignal:
    """generate_sell_signal() 함수 테스트"""
    
    def test_normal_sell_signal(self):
        """통상 매도 신호 생성"""
        df = pd.DataFrame({
            'Stage': [2, 3, 3, 4],
            'Dir_MACD_상': ['down', 'down', 'down', 'down'],
            'Dir_MACD_중': ['down', 'down', 'up', 'down'],
            'Dir_MACD_하': ['down', 'down', 'down', 'down'],
            'Close': [50000, 49000, 48000, 47000]
        })
        
        result = generate_sell_signal(df, 'normal')
        
        # 제3스테이지 + 3개 MACD 하락 = 신호 발생
        assert result['Sell_Signal'].iloc[1] == 1  # 조건 충족
        assert result['Sell_Signal'].iloc[0] == 0  # 제2스테이지 (통상 매도 X)
        assert result['Sell_Signal'].iloc[2] == 0  # MACD 중 상승
        assert result['Sell_Signal'].iloc[3] == 0  # 제4스테이지
        
        # 신호 발생 이유
        assert '통상 매도' in result['Signal_Reason'].iloc[1]
    
    def test_early_sell_signal(self):
        """조기 매도 신호 생성"""
        df = pd.DataFrame({
            'Stage': [1, 2, 2, 3],
            'Dir_MACD_상': ['down', 'down', 'up', 'down'],
            'Dir_MACD_중': ['down', 'down', 'down', 'down'],
            'Dir_MACD_하': ['down', 'down', 'down', 'down'],
            'Close': [51000, 50000, 49000, 48000]
        })
        
        result = generate_sell_signal(df, 'early')
        
        # 제2스테이지 + 3개 MACD 하락 = 조기 매도 신호
        assert result['Sell_Signal'].iloc[1] == 2  # 조건 충족
        assert result['Sell_Signal'].iloc[0] == 0  # 제1스테이지
        assert result['Sell_Signal'].iloc[2] == 0  # MACD 상 상승
        assert result['Sell_Signal'].iloc[3] == 0  # 제3스테이지 (조기 매도 X)
        
        # 신호 발생 이유
        assert '조기 매도' in result['Signal_Reason'].iloc[1]
    
    def test_no_sell_signal(self):
        """매도 신호 없음"""
        df = pd.DataFrame({
            'Stage': [4, 5, 6, 1],
            'Dir_MACD_상': ['down', 'up', 'up', 'up'],
            'Dir_MACD_중': ['down', 'up', 'up', 'up'],
            'Dir_MACD_하': ['down', 'up', 'up', 'up'],
            'Close': [47000, 48000, 49000, 50000]
        })
        
        result = generate_sell_signal(df, 'normal')
        
        # 모든 행에서 신호 없음
        assert (result['Sell_Signal'] == 0).all()


class TestCheckEntryConditions:
    """check_entry_conditions() 함수 테스트"""
    
    def test_buy_conditions_met(self):
        """매수 조건 충족"""
        df = pd.DataFrame({
            'Stage': [6],
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['up'],
            'Dir_MACD_하': ['up']
        })
        
        result = check_entry_conditions(df, 'buy')
        
        assert result['stage_ok'] is True
        assert result['macd_ok'] is True
        assert result['all_ok'] is True
        assert result['current_stage'] == 6
        assert result['macd_directions'] == {'상': 'up', '중': 'up', '하': 'up'}
        assert '매수 조건 충족' in result['details']
    
    def test_buy_conditions_stage_fail(self):
        """매수 스테이지 조건 미충족"""
        df = pd.DataFrame({
            'Stage': [1],
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['up'],
            'Dir_MACD_하': ['up']
        })
        
        result = check_entry_conditions(df, 'buy')
        
        assert result['stage_ok'] is False
        assert result['macd_ok'] is True
        assert result['all_ok'] is False
        assert '스테이지 미충족' in result['details']
    
    def test_buy_conditions_macd_fail(self):
        """매수 MACD 조건 미충족"""
        df = pd.DataFrame({
            'Stage': [6],
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['down'],
            'Dir_MACD_하': ['up']
        })
        
        result = check_entry_conditions(df, 'buy')
        
        assert result['stage_ok'] is True
        assert result['macd_ok'] is False
        assert result['all_ok'] is False
        assert 'MACD 미충족' in result['details']
    
    def test_sell_conditions_met(self):
        """매도 조건 충족"""
        df = pd.DataFrame({
            'Stage': [3],
            'Dir_MACD_상': ['down'],
            'Dir_MACD_중': ['down'],
            'Dir_MACD_하': ['down']
        })
        
        result = check_entry_conditions(df, 'sell')
        
        assert result['stage_ok'] is True
        assert result['macd_ok'] is True
        assert result['all_ok'] is True
        assert result['current_stage'] == 3
        assert result['macd_directions'] == {'상': 'down', '중': 'down', '하': 'down'}
        assert '매도 조건 충족' in result['details']
    
    def test_check_conditions_invalid_position_type(self):
        """잘못된 position_type"""
        df = pd.DataFrame({
            'Stage': [6],
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['up'],
            'Dir_MACD_하': ['up']
        })
        
        with pytest.raises(ValueError, match="'buy' 또는 'sell'"):
            check_entry_conditions(df, 'invalid')
    
    def test_check_conditions_empty_data(self):
        """빈 데이터"""
        df = pd.DataFrame({
            'Stage': [],
            'Dir_MACD_상': [],
            'Dir_MACD_중': [],
            'Dir_MACD_하': []
        })
        
        with pytest.raises(ValueError, match="데이터가 비어 있습니다"):
            check_entry_conditions(df, 'buy')


class TestGenerateEntrySignals:
    """generate_entry_signals() 함수 테스트"""
    
    def test_normal_signals_only(self):
        """통상 신호만 (조기 신호 비활성화)"""
        df = pd.DataFrame({
            'Stage': [5, 6, 2, 3],
            'Dir_MACD_상': ['up', 'up', 'down', 'down'],
            'Dir_MACD_중': ['up', 'up', 'down', 'down'],
            'Dir_MACD_하': ['up', 'up', 'down', 'down'],
            'Close': [49000, 50000, 50000, 49000]
        })
        
        result = generate_entry_signals(df, enable_early=False)
        
        # 통상 매수 신호
        assert result['Entry_Signal'].iloc[1] == 1
        assert result['Signal_Type'].iloc[1] == 'buy'
        
        # 통상 매도 신호
        assert result['Entry_Signal'].iloc[3] == -1
        assert result['Signal_Type'].iloc[3] == 'sell'
        
        # 조기 신호 없음
        assert result['Entry_Signal'].iloc[0] == 0  # 제5 (조기 매수 X)
        assert result['Entry_Signal'].iloc[2] == 0  # 제2 (조기 매도 X)
    
    def test_with_early_signals(self):
        """조기 신호 포함"""
        df = pd.DataFrame({
            'Stage': [5, 6, 2, 3],
            'Dir_MACD_상': ['up', 'up', 'down', 'down'],
            'Dir_MACD_중': ['up', 'up', 'down', 'down'],
            'Dir_MACD_하': ['up', 'up', 'down', 'down'],
            'Close': [49000, 50000, 50000, 49000]
        })
        
        result = generate_entry_signals(df, enable_early=True)
        
        # 통상 매수 신호 (우선순위 높음)
        assert result['Entry_Signal'].iloc[1] == 1
        assert result['Signal_Type'].iloc[1] == 'buy'
        
        # 조기 매수 신호
        assert result['Entry_Signal'].iloc[0] == 2
        assert result['Signal_Type'].iloc[0] == 'buy'
        
        # 조기 매도 신호
        assert result['Entry_Signal'].iloc[2] == -2
        assert result['Signal_Type'].iloc[2] == 'sell'
        
        # 통상 매도 신호 (우선순위 높음)
        assert result['Entry_Signal'].iloc[3] == -1
        assert result['Signal_Type'].iloc[3] == 'sell'
    
    def test_no_signals(self):
        """신호 없음"""
        df = pd.DataFrame({
            'Stage': [1, 4],
            'Dir_MACD_상': ['up', 'down'],
            'Dir_MACD_중': ['up', 'down'],
            'Dir_MACD_하': ['up', 'down'],
            'Close': [50000, 48000]
        })
        
        result = generate_entry_signals(df, enable_early=False)
        
        # 모든 신호 0
        assert (result['Entry_Signal'] == 0).all()
        assert result['Signal_Type'].isna().all()
    
    def test_signal_priority(self):
        """신호 우선순위 (통상 > 조기)"""
        df = pd.DataFrame({
            'Stage': [6],  # 제6스테이지 = 통상 매수 조건 + 조기 매수 조건 모두 충족
            'Dir_MACD_상': ['up'],
            'Dir_MACD_중': ['up'],
            'Dir_MACD_하': ['up'],
            'Close': [50000]
        })
        
        result = generate_entry_signals(df, enable_early=True)
        
        # 통상 매수 신호가 우선
        assert result['Entry_Signal'].iloc[0] == 1  # 통상 매수 (2가 아님)
        assert result['Signal_Type'].iloc[0] == 'buy'
    
    def test_entry_signals_invalid_input(self):
        """잘못된 입력"""
        with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
            generate_entry_signals([1, 2, 3], False)
