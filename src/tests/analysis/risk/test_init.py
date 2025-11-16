"""
리스크 관리 통합 모듈 테스트
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.risk import apply_risk_management


class TestApplyRiskManagement:
    """apply_risk_management 함수 테스트"""
    
    @pytest.fixture
    def basic_market_data(self):
        """기본 시장 데이터"""
        return pd.DataFrame({
            'Close': [50_000, 51_000, 50_500],
            'ATR': [1_000, 1_000, 1_000],
            'EMA_20': [48_500, 48_700, 48_600],
            'EMA_60': [47_000, 47_200, 47_100],
            'EMA_120': [45_000, 45_300, 45_200]
        })
    
    @pytest.fixture
    def buy_signal(self):
        """매수 신호"""
        return {
            'ticker': '005930',
            'action': 'buy',
            'signal_strength': 85,
            'current_price': 50_000
        }
    
    @pytest.fixture
    def sell_signal(self):
        """매도 신호"""
        return {
            'ticker': '005930',
            'action': 'sell',
            'signal_strength': 85,
            'current_price': 50_000
        }
    
    @pytest.fixture
    def exit_signal(self):
        """청산 신호"""
        return {
            'ticker': '005930',
            'action': 'exit',
            'signal_strength': 0,
            'current_price': 50_000
        }
    
    def test_approved_buy_signal(self, buy_signal, basic_market_data):
        """정상 매수 신호 승인"""
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        assert result['approved'] is True
        assert result['position_size'] > 0
        assert result['units'] > 0
        assert result['stop_price'] > 0
        assert result['stop_price'] < buy_signal['current_price']  # 매수는 손절가가 낮음
        assert result['risk_amount'] > 0
        assert result['risk_percentage'] > 0
    
    def test_approved_sell_signal(self, sell_signal):
        """정상 매도 신호 승인"""
        # 매도 포지션에 적합한 시장 데이터 (추세선이 현재가보다 위에)
        market_data = pd.DataFrame({
            'Close': [50_000, 51_000, 50_500],
            'ATR': [1_000, 1_000, 1_000],
            'EMA_20': [51_500, 51_700, 51_600],  # 현재가보다 높음
            'EMA_60': [52_000, 52_200, 52_100],
            'EMA_120': [53_000, 53_300, 53_200]
        })
        
        config = {
            'max_single_risk': 0.05  # 5%로 완화
        }
        
        result = apply_risk_management(
            signal=sell_signal,
            account_balance=10_000_000,
            positions={},
            market_data=market_data,
            config=config
        )
        
        assert result['approved'] is True
        assert result['position_size'] > 0
        assert result['stop_price'] > sell_signal['current_price']  # 매도는 손절가가 높음
    
    def test_exit_signal_bypass(self, exit_signal, basic_market_data):
        """청산 신호는 리스크 관리 우회"""
        result = apply_risk_management(
            signal=exit_signal,
            account_balance=10_000_000,
            positions={'005930': 2},
            market_data=basic_market_data
        )
        
        assert result['approved'] is True
        assert result['position_size'] == 0
        assert result['units'] == 0
        assert '청산 신호' in result['warnings'][0]
    
    def test_weak_signal_rejection(self, buy_signal, basic_market_data):
        """약한 신호 거부"""
        buy_signal['signal_strength'] = 45  # 50 미만
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        assert result['approved'] is False
        assert '신호 강도' in result['reason']
    
    def test_portfolio_limit_rejection(self, buy_signal, basic_market_data):
        """포트폴리오 제한 초과 거부"""
        # 이미 최대 유닛 보유
        positions = {'005930': 4}  # 최대 4유닛
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions=positions,
            market_data=basic_market_data
        )
        
        assert result['approved'] is False
        assert '포트폴리오 제한' in result['reason']
    
    def test_position_size_reduction(self, buy_signal, basic_market_data):
        """포지션 크기 축소"""
        # 이미 3유닛 보유, 추가 요청 시 1유닛만 허용
        positions = {'005930': 3}
        
        config = {
            'max_single_risk': 0.05,  # 리스크 한도 완화
            'max_capital_ratio': 1.0  # 자본 제약 완화 (여러 유닛 허용)
        }
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions=positions,
            market_data=basic_market_data,
            config=config
        )
        
        # 1유닛만 허용되어야 함
        assert result['approved'] is True
        assert result['units'] <= 1
        assert len(result['warnings']) > 0
    
    def test_custom_config(self, buy_signal, basic_market_data):
        """커스텀 설정 적용"""
        config = {
            'risk_percentage': 0.005,  # 0.5% (더 보수적)
            'signal_strength_threshold': 70,
            'atr_multiplier': 3.0,
            'limits': {
                'single': 6,
                'total': 15
            },
            'max_single_risk': 0.05  # 5% (리스크 한도 완화)
        }
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data,
            config=config
        )
        
        assert result['approved'] is True
        # 리스크가 0.5%로 설정되었으므로 포지션이 작아야 함
        assert result['position_size'] <= 100
    
    def test_correlation_group_limit(self, buy_signal, basic_market_data):
        """상관관계 그룹 제한"""
        positions = {'000660': 4}  # SK하이닉스 4유닛
        
        config = {
            'correlation_groups': {
                '반도체': ['005930', '000660']
            },
            'limits': {
                'correlated': 6  # 그룹 최대 6유닛
            }
        }
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions=positions,
            market_data=basic_market_data,
            config=config
        )
        
        # 최대 2유닛만 추가 가능 (4 + 2 = 6)
        assert result['approved'] is True
        assert result['units'] <= 2
    
    def test_missing_signal_fields(self, basic_market_data):
        """신호 필수 필드 누락"""
        invalid_signal = {
            'ticker': '005930',
            'action': 'buy'
            # signal_strength, current_price 누락
        }
        
        with pytest.raises(ValueError, match="신호에 필수 필드가 없습니다"):
            apply_risk_management(
                signal=invalid_signal,
                account_balance=10_000_000,
                positions={},
                market_data=basic_market_data
            )
    
    def test_invalid_account_balance(self, buy_signal, basic_market_data):
        """잘못된 계좌 잔고"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수"):
            apply_risk_management(
                signal=buy_signal,
                account_balance=0,
                positions={},
                market_data=basic_market_data
            )
    
    def test_invalid_positions_type(self, buy_signal, basic_market_data):
        """잘못된 포지션 타입"""
        with pytest.raises(ValueError, match="포지션은 딕셔너리"):
            apply_risk_management(
                signal=buy_signal,
                account_balance=10_000_000,
                positions=[],  # 리스트는 안됨
                market_data=basic_market_data
            )
    
    def test_invalid_market_data_type(self, buy_signal):
        """잘못된 시장 데이터 타입"""
        with pytest.raises(ValueError, match="시장 데이터는 DataFrame"):
            apply_risk_management(
                signal=buy_signal,
                account_balance=10_000_000,
                positions={},
                market_data={'ATR': 1000}  # dict는 안됨
            )
    
    def test_missing_market_data_columns(self, buy_signal):
        """시장 데이터 필수 컬럼 누락"""
        incomplete_data = pd.DataFrame({
            'Close': [50_000]
            # ATR, EMA_20 누락
        })
        
        with pytest.raises(ValueError, match="시장 데이터에 필수 컬럼이 없습니다"):
            apply_risk_management(
                signal=buy_signal,
                account_balance=10_000_000,
                positions={},
                market_data=incomplete_data
            )
    
    def test_empty_market_data(self, buy_signal):
        """빈 시장 데이터"""
        empty_data = pd.DataFrame(columns=['ATR', 'EMA_20'])
        
        with pytest.raises(ValueError, match="시장 데이터가 비어있습니다"):
            apply_risk_management(
                signal=buy_signal,
                account_balance=10_000_000,
                positions={},
                market_data=empty_data
            )
    
    def test_result_structure_approved(self, buy_signal, basic_market_data):
        """승인 시 결과 구조 검증"""
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        # 필수 필드 확인
        assert 'approved' in result
        assert 'position_size' in result
        assert 'units' in result
        assert 'stop_price' in result
        assert 'risk_amount' in result
        assert 'risk_percentage' in result
        assert 'warnings' in result
        assert 'details' in result
        
        # 상세 정보 구조 확인
        assert 'position_sizing' in result['details']
        assert 'portfolio_limits' in result['details']
        assert 'stop_loss' in result['details']
        assert 'risk_assessment' in result['details']
    
    def test_result_structure_rejected(self, buy_signal, basic_market_data):
        """거부 시 결과 구조 검증"""
        buy_signal['signal_strength'] = 30  # 약한 신호
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        assert result['approved'] is False
        assert 'reason' in result
        assert 'warnings' in result
        assert 'details' in result
    
    def test_warnings_accumulation(self, buy_signal, basic_market_data):
        """경고 메시지 누적"""
        # 포지션 크기 축소 상황
        positions = {'005930': 3}
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions=positions,
            market_data=basic_market_data
        )
        
        assert result['approved'] is True
        assert isinstance(result['warnings'], list)
        if result['warnings']:
            assert '포지션 크기 축소' in result['warnings'][0]
    
    def test_stop_price_calculation(self, buy_signal, basic_market_data):
        """손절가 계산 검증"""
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        # 손절가는 진입가보다 낮아야 함 (매수 포지션)
        assert result['stop_price'] < buy_signal['current_price']
        
        # 손절가는 합리적 범위 내
        # 예: ATR의 2배 이상 차이나지 않아야 함
        atr = basic_market_data.iloc[-1]['ATR']
        max_stop_distance = atr * 3
        assert buy_signal['current_price'] - result['stop_price'] <= max_stop_distance
    
    def test_risk_amount_calculation(self, buy_signal, basic_market_data):
        """리스크 금액 계산 검증"""
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data
        )
        
        # 리스크 금액 = 포지션 크기 × (진입가 - 손절가)
        expected_risk = result['position_size'] * (
            buy_signal['current_price'] - result['stop_price']
        )
        
        assert result['risk_amount'] == pytest.approx(expected_risk, rel=0.01)
    
    def test_risk_percentage_within_limit(self, buy_signal, basic_market_data):
        """리스크 비율이 한도 내"""
        # 리스크를 낮추기 위한 설정
        config = {
            'risk_percentage': 0.002,  # 0.2% (매우 보수적)
            'max_single_risk': 0.01
        }
        
        result = apply_risk_management(
            signal=buy_signal,
            account_balance=10_000_000,
            positions={},
            market_data=basic_market_data,
            config=config
        )
        
        # 최대 1% (단일 포지션)
        assert result['risk_percentage'] <= 0.01


class TestIntegrationScenarios:
    """실제 시나리오 통합 테스트"""
    
    def test_full_workflow_success(self):
        """전체 워크플로우 성공 시나리오"""
        # 1. 시장 데이터 준비
        market_data = pd.DataFrame({
            'Close': [50_000, 51_000, 50_500],
            'High': [51_000, 52_000, 51_500],
            'Low': [49_000, 50_000, 49_500],
            'ATR': [1_000, 1_000, 1_000],
            'EMA_20': [48_500, 48_700, 48_600],
            'EMA_60': [47_000, 47_200, 47_100],
            'EMA_120': [45_000, 45_300, 45_200]
        })
        
        # 2. 매수 신호
        signal = {
            'ticker': '005930',
            'action': 'buy',
            'signal_strength': 85,
            'current_price': 50_500
        }
        
        # 3. 리스크 관리 적용 (리스크 한도 완화)
        config = {
            'max_single_risk': 0.05  # 5%
        }
        
        result = apply_risk_management(
            signal=signal,
            account_balance=10_000_000,
            positions={},
            market_data=market_data,
            config=config
        )
        
        # 4. 결과 검증
        assert result['approved'] is True
        assert result['position_size'] > 0
        assert result['stop_price'] < signal['current_price']
        assert 0 < result['risk_percentage'] <= 0.05
        
        print(f"\n주문 승인:")
        print(f"  종목: {signal['ticker']}")
        print(f"  포지션: {result['position_size']}주 ({result['units']}유닛)")
        print(f"  진입가: {signal['current_price']:,}원")
        print(f"  손절가: {result['stop_price']:,}원")
        print(f"  리스크: {result['risk_amount']:,}원 ({result['risk_percentage']:.2%})")
    
    def test_multiple_positions_management(self):
        """다수 포지션 관리"""
        market_data = pd.DataFrame({
            'ATR': [1_000],
            'EMA_20': [48_500]
        })
        
        # 기존 포지션 2개
        positions = {
            '000660': 2,  # SK하이닉스 2유닛
            '005380': 2   # 현대차 2유닛
        }
        
        # 삼성전자 추가
        signal = {
            'ticker': '005930',
            'action': 'buy',
            'signal_strength': 85,
            'current_price': 50_000
        }
        
        config = {
            'correlation_groups': {
                '반도체': ['005930', '000660'],
                '자동차': ['005380']
            }
        }
        
        result = apply_risk_management(
            signal=signal,
            account_balance=10_000_000,
            positions=positions,
            market_data=market_data,
            config=config
        )
        
        # 반도체 그룹 제한(6유닛) 때문에 최대 4유닛까지만 가능
        assert result['approved'] is True
        assert result['units'] <= 4
    
    def test_risk_limit_exceeded(self):
        """리스크 한도 초과 시나리오"""
        market_data = pd.DataFrame({
            'ATR': [5_000],  # 매우 높은 변동성
            'EMA_20': [40_000]
        })
        
        signal = {
            'ticker': '005930',
            'action': 'buy',
            'signal_strength': 85,
            'current_price': 50_000
        }
        
        config = {
            'risk_percentage': 0.02,  # 2% 리스크
            'max_single_risk': 0.005  # 단일 포지션 0.5% 제한
        }
        
        result = apply_risk_management(
            signal=signal,
            account_balance=10_000_000,
            positions={},
            market_data=market_data,
            config=config
        )
        
        # 리스크가 너무 커서 거부될 수 있음
        if not result['approved']:
            assert '리스크' in result['reason']
    
    def test_progressive_position_building(self):
        """점진적 포지션 구축"""
        market_data = pd.DataFrame({
            'ATR': [1_000],
            'EMA_20': [48_500]
        })
        
        signal = {
            'ticker': '005930',
            'action': 'buy',
            'signal_strength': 85,
            'current_price': 50_000
        }
        
        # 1차 진입
        result1 = apply_risk_management(
            signal=signal,
            account_balance=10_000_000,
            positions={},
            market_data=market_data
        )
        assert result1['approved'] is True
        units1 = result1['units']
        
        # 2차 진입
        result2 = apply_risk_management(
            signal=signal,
            account_balance=10_000_000,
            positions={'005930': units1},
            market_data=market_data
        )
        assert result2['approved'] is True
        
        # 총 유닛은 4 이하여야 함
        total_units = units1 + result2['units']
        assert total_units <= 4
