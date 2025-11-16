"""
리스크 노출 관리 모듈 테스트
"""

import pytest
from src.analysis.risk.exposure import (
    calculate_position_risk,
    calculate_total_portfolio_risk,
    check_risk_limits,
    generate_risk_report
)


class TestCalculatePositionRisk:
    """calculate_position_risk 함수 테스트"""
    
    def test_long_position_basic(self):
        """매수 포지션 기본 리스크 계산"""
        result = calculate_position_risk(
            position_size=100,
            entry_price=50_000,
            stop_price=48_000,
            position_type='long'
        )
        
        assert result['risk_per_share'] == 2_000
        assert result['total_risk'] == 200_000
        assert result['risk_percentage'] == pytest.approx(0.04)
        assert result['position_value'] == 5_000_000
    
    def test_short_position_basic(self):
        """매도 포지션 기본 리스크 계산"""
        result = calculate_position_risk(
            position_size=50,
            entry_price=100_000,
            stop_price=104_000,
            position_type='short'
        )
        
        assert result['risk_per_share'] == 4_000
        assert result['total_risk'] == 200_000
        assert result['risk_percentage'] == pytest.approx(0.04)
        assert result['position_value'] == 5_000_000
    
    def test_zero_position_size(self):
        """포지션 크기가 0인 경우"""
        result = calculate_position_risk(
            position_size=0,
            entry_price=50_000,
            stop_price=48_000,
            position_type='long'
        )
        
        assert result['total_risk'] == 0
        assert result['position_value'] == 0
    
    def test_small_stop_distance(self):
        """손절 거리가 작은 경우"""
        result = calculate_position_risk(
            position_size=1000,
            entry_price=10_000,
            stop_price=9_900,
            position_type='long'
        )
        
        assert result['risk_per_share'] == 100
        assert result['total_risk'] == 100_000
        assert result['risk_percentage'] == pytest.approx(0.01)
    
    def test_large_stop_distance(self):
        """손절 거리가 큰 경우"""
        result = calculate_position_risk(
            position_size=10,
            entry_price=100_000,
            stop_price=80_000,
            position_type='long'
        )
        
        assert result['risk_per_share'] == 20_000
        assert result['total_risk'] == 200_000
        assert result['risk_percentage'] == pytest.approx(0.2)
    
    def test_negative_position_size(self):
        """음수 포지션 크기"""
        with pytest.raises(ValueError, match="포지션 크기는 0 이상"):
            calculate_position_risk(-100, 50_000, 48_000, 'long')
    
    def test_zero_entry_price(self):
        """진입가가 0인 경우"""
        with pytest.raises(ValueError, match="진입가는 양수"):
            calculate_position_risk(100, 0, 48_000, 'long')
    
    def test_negative_entry_price(self):
        """음수 진입가"""
        with pytest.raises(ValueError, match="진입가는 양수"):
            calculate_position_risk(100, -50_000, 48_000, 'long')
    
    def test_zero_stop_price(self):
        """손절가가 0인 경우"""
        with pytest.raises(ValueError, match="손절가는 양수"):
            calculate_position_risk(100, 50_000, 0, 'long')
    
    def test_negative_stop_price(self):
        """음수 손절가"""
        with pytest.raises(ValueError, match="손절가는 양수"):
            calculate_position_risk(100, 50_000, -48_000, 'long')
    
    def test_invalid_position_type(self):
        """잘못된 포지션 타입"""
        with pytest.raises(ValueError, match="포지션 타입은 'long' 또는 'short'"):
            calculate_position_risk(100, 50_000, 48_000, 'invalid')
    
    def test_long_stop_above_entry(self):
        """매수 포지션에서 손절가가 진입가보다 높은 경우"""
        with pytest.raises(ValueError, match="매수 포지션의 손절가는 진입가보다 낮아야"):
            calculate_position_risk(100, 50_000, 52_000, 'long')
    
    def test_short_stop_below_entry(self):
        """매도 포지션에서 손절가가 진입가보다 낮은 경우"""
        with pytest.raises(ValueError, match="매도 포지션의 손절가는 진입가보다 높아야"):
            calculate_position_risk(100, 50_000, 48_000, 'short')
    
    def test_float_position_size(self):
        """실수 포지션 크기 (numbers.Number 타입)"""
        result = calculate_position_risk(
            position_size=100.0,
            entry_price=50_000,
            stop_price=48_000,
            position_type='long'
        )
        
        assert result['total_risk'] == 200_000


class TestCalculateTotalPortfolioRisk:
    """calculate_total_portfolio_risk 함수 테스트"""
    
    def test_single_position(self):
        """단일 포지션"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        result = calculate_total_portfolio_risk(positions, 10_000_000)
        
        assert result['total_risk'] == 200_000
        assert result['risk_percentage'] == pytest.approx(0.02)
        assert result['positions_at_risk'] == 1
        assert '005930' in result['risk_by_ticker']
        assert result['largest_risk']['ticker'] == '005930'
    
    def test_multiple_positions(self):
        """다수 포지션"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 50,
                'entry_price': 100_000,
                'stop_price': 96_000,
                'type': 'long'
            },
            {
                'ticker': '005380',
                'size': 200,
                'entry_price': 25_000,
                'stop_price': 24_000,
                'type': 'long'
            }
        ]
        
        result = calculate_total_portfolio_risk(positions, 10_000_000)
        
        # 총 리스크: 200,000 + 200,000 + 200,000 = 600,000
        assert result['total_risk'] == 600_000
        assert result['risk_percentage'] == pytest.approx(0.06)
        assert result['positions_at_risk'] == 3
        assert len(result['risk_by_ticker']) == 3
    
    def test_mixed_position_types(self):
        """매수/매도 혼합 포지션"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 50,
                'entry_price': 100_000,
                'stop_price': 104_000,
                'type': 'short'
            }
        ]
        
        result = calculate_total_portfolio_risk(positions, 10_000_000)
        
        assert result['total_risk'] == 400_000
        assert result['positions_at_risk'] == 2
    
    def test_empty_positions(self):
        """빈 포지션 리스트"""
        result = calculate_total_portfolio_risk([], 10_000_000)
        
        assert result['total_risk'] == 0
        assert result['risk_percentage'] == 0
        assert result['positions_at_risk'] == 0
        assert result['largest_risk'] is None
        assert result['risk_by_ticker'] == {}
    
    def test_largest_risk_identification(self):
        """최대 리스크 포지션 식별"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 50,
                'entry_price': 100_000,
                'stop_price': 95_000,  # 리스크가 더 큼
                'type': 'long'
            }
        ]
        
        result = calculate_total_portfolio_risk(positions, 10_000_000)
        
        assert result['largest_risk']['ticker'] == '000660'
        assert result['largest_risk']['total_risk'] == 250_000
    
    def test_zero_account_balance(self):
        """계좌 잔고가 0인 경우"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        with pytest.raises(ValueError, match="계좌 잔고는 양수"):
            calculate_total_portfolio_risk(positions, 0)
    
    def test_negative_account_balance(self):
        """음수 계좌 잔고"""
        positions = []
        
        with pytest.raises(ValueError, match="계좌 잔고는 양수"):
            calculate_total_portfolio_risk(positions, -10_000_000)
    
    def test_not_list_positions(self):
        """포지션이 리스트가 아닌 경우"""
        with pytest.raises(ValueError, match="포지션은 리스트"):
            calculate_total_portfolio_risk("not a list", 10_000_000)
    
    def test_missing_required_fields(self):
        """필수 필드 누락"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                # entry_price 누락
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        with pytest.raises(ValueError, match="필수 필드가 없습니다"):
            calculate_total_portfolio_risk(positions, 10_000_000)
    
    def test_risk_by_ticker_details(self):
        """종목별 리스크 상세 정보"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        result = calculate_total_portfolio_risk(positions, 10_000_000)
        ticker_risk = result['risk_by_ticker']['005930']
        
        assert ticker_risk['total_risk'] == 200_000
        assert ticker_risk['risk_per_share'] == 2_000
        assert ticker_risk['risk_percentage'] == pytest.approx(0.04)
        assert ticker_risk['position_value'] == 5_000_000
        assert ticker_risk['size'] == 100


class TestCheckRiskLimits:
    """check_risk_limits 함수 테스트"""
    
    def test_within_limits(self):
        """한도 내 리스크"""
        result = check_risk_limits(
            total_risk=150_000,
            account_balance=10_000_000,
            max_risk_percentage=0.02,
            max_single_risk=0.01
        )
        
        assert result['within_limits'] is True
        assert result['total_risk_ok'] is True
        assert result['risk_percentage'] == pytest.approx(0.015)
        assert result['available_risk'] == 50_000
        assert len(result['warnings']) == 0
    
    def test_exceed_total_limit(self):
        """총 리스크 한도 초과"""
        result = check_risk_limits(
            total_risk=250_000,
            account_balance=10_000_000,
            max_risk_percentage=0.02
        )
        
        assert result['within_limits'] is False
        assert result['total_risk_ok'] is False
        assert result['available_risk'] == 0
        assert len(result['warnings']) > 0
        assert "총 리스크가 한도를 초과" in result['warnings'][0]
    
    def test_single_position_limit_check(self):
        """단일 포지션 리스크 한도 체크"""
        positions_risk = {
            '005930': {'total_risk': 80_000},
            '000660': {'total_risk': 120_000}  # 1% 한도 초과
        }
        
        result = check_risk_limits(
            total_risk=200_000,
            account_balance=10_000_000,
            positions_risk=positions_risk,
            max_risk_percentage=0.03,
            max_single_risk=0.01
        )
        
        assert result['within_limits'] is False
        assert result['total_risk_ok'] is True
        assert result['single_risk_ok'] is False
        assert len(result['warnings']) > 0
    
    def test_near_limit_warning(self):
        """한도 근접 시 경고"""
        result = check_risk_limits(
            total_risk=185_000,  # 90% 이상
            account_balance=10_000_000,
            max_risk_percentage=0.02
        )
        
        assert result['within_limits'] is True
        assert result['total_risk_ok'] is True
        assert len(result['warnings']) > 0
        assert "90%에 근접" in result['warnings'][0]
    
    def test_zero_risk(self):
        """리스크가 0인 경우"""
        result = check_risk_limits(
            total_risk=0,
            account_balance=10_000_000
        )
        
        assert result['within_limits'] is True
        assert result['total_risk_ok'] is True
        assert result['risk_percentage'] == 0
        assert result['available_risk'] == 200_000
    
    def test_custom_limits(self):
        """커스텀 한도 설정"""
        result = check_risk_limits(
            total_risk=300_000,
            account_balance=10_000_000,
            max_risk_percentage=0.05,  # 5%
            max_single_risk=0.02  # 2%
        )
        
        assert result['within_limits'] is True
        assert result['total_risk_ok'] is True
        assert result['available_risk'] == 200_000
    
    def test_negative_total_risk(self):
        """음수 총 리스크"""
        with pytest.raises(ValueError, match="총 리스크는 0 이상"):
            check_risk_limits(-100_000, 10_000_000)
    
    def test_zero_account_balance(self):
        """계좌 잔고가 0인 경우"""
        with pytest.raises(ValueError, match="계좌 잔고는 양수"):
            check_risk_limits(100_000, 0)
    
    def test_invalid_max_risk_percentage(self):
        """잘못된 최대 리스크 비율"""
        with pytest.raises(ValueError, match="최대 리스크 비율은 0~1 사이"):
            check_risk_limits(100_000, 10_000_000, max_risk_percentage=1.5)
    
    def test_invalid_max_single_risk(self):
        """잘못된 단일 포지션 최대 리스크"""
        with pytest.raises(ValueError, match="단일 포지션 최대 리스크는 0~1 사이"):
            check_risk_limits(100_000, 10_000_000, max_single_risk=0)


class TestGenerateRiskReport:
    """generate_risk_report 함수 테스트"""
    
    def test_basic_report(self):
        """기본 리포트 생성"""
        positions = [
            {
                'ticker': '005930',
                'size': 50,
                'entry_price': 50_000,
                'stop_price': 49_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 25,
                'entry_price': 100_000,
                'stop_price': 98_000,
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(positions, 10_000_000)
        
        # 요약 정보 확인
        assert report['summary']['total_positions'] == 2
        assert report['summary']['total_risk'] == 100_000  # 50,000 + 50,000
        assert report['summary']['risk_percentage'] == pytest.approx(0.01)
        assert report['summary']['within_limits'] is True
        
        # 종목별 리스크 확인
        assert '005930' in report['by_ticker']
        assert '000660' in report['by_ticker']
        
        # 한도 체크 결과 확인
        assert 'limits' in report
        assert report['limits']['within_limits'] is True
    
    def test_report_with_correlation_groups(self):
        """상관관계 그룹 포함 리포트"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 50,
                'entry_price': 100_000,
                'stop_price': 96_000,
                'type': 'long'
            },
            {
                'ticker': '005380',
                'size': 200,
                'entry_price': 25_000,
                'stop_price': 24_000,
                'type': 'long'
            }
        ]
        
        correlation_groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        report = generate_risk_report(
            positions, 
            10_000_000,
            correlation_groups=correlation_groups
        )
        
        # 그룹별 리스크 확인
        assert report['by_group'] is not None
        assert '반도체' in report['by_group']
        assert '자동차' in report['by_group']
        
        # 반도체 그룹 상세 확인
        semiconductor = report['by_group']['반도체']
        assert semiconductor['total_risk'] == 400_000
        assert semiconductor['position_count'] == 2
        assert '005930' in semiconductor['positions']
        assert '000660' in semiconductor['positions']
    
    def test_report_with_warnings(self):
        """경고가 있는 리포트"""
        positions = [
            {
                'ticker': f'00{i:04d}',
                'size': 50,
                'entry_price': 10_000,
                'stop_price': 9_800,
                'type': 'long'
            }
            for i in range(7)  # 7개 포지션
        ]
        
        report = generate_risk_report(positions, 10_000_000)
        
        # 보유 포지션이 많다는 경고 확인
        assert len(report['warnings']) > 0
        warning_found = any('보유 포지션이 많습니다' in w for w in report['warnings'])
        assert warning_found
    
    def test_report_largest_risk_warning(self):
        """최대 리스크 포지션 경고"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 46_000,  # 큰 리스크
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(
            positions,
            10_000_000,
            max_single_risk=0.05
        )
        
        # 최대 리스크 포지션 정보 확인
        assert report['largest_risk'] is not None
        assert report['largest_risk']['ticker'] == '005930'
    
    def test_empty_positions_report(self):
        """빈 포지션 리포트"""
        report = generate_risk_report([], 10_000_000)
        
        assert report['summary']['total_positions'] == 0
        assert report['summary']['total_risk'] == 0
        assert report['summary']['risk_percentage'] == 0
        assert report['by_ticker'] == {}
    
    def test_ticker_risk_details(self):
        """종목별 리스크 상세 정보"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(positions, 10_000_000)
        ticker_info = report['by_ticker']['005930']
        
        assert ticker_info['total_risk'] == 200_000
        assert ticker_info['risk_per_share'] == 2_000
        assert ticker_info['entry_price'] == 50_000
        assert ticker_info['stop_price'] == 48_000
        assert ticker_info['type'] == 'long'
        assert ticker_info['risk_ratio'] == pytest.approx(0.02)
    
    def test_custom_risk_limits(self):
        """커스텀 리스크 한도로 리포트 생성"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 47_000,
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(
            positions,
            10_000_000,
            max_risk_percentage=0.05,
            max_single_risk=0.04
        )
        
        assert report['limits']['within_limits'] is True
    
    def test_invalid_account_balance(self):
        """잘못된 계좌 잔고"""
        positions = []
        
        with pytest.raises(ValueError, match="계좌 잔고는 양수"):
            generate_risk_report(positions, 0)
    
    def test_invalid_positions_type(self):
        """잘못된 포지션 타입"""
        with pytest.raises(ValueError, match="포지션은 리스트"):
            generate_risk_report("not a list", 10_000_000)
    
    def test_group_without_positions(self):
        """포지션이 없는 그룹은 제외"""
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            }
        ]
        
        correlation_groups = {
            '반도체': ['005930'],
            '자동차': ['005380', '000270']  # 포지션 없음
        }
        
        report = generate_risk_report(
            positions,
            10_000_000,
            correlation_groups=correlation_groups
        )
        
        # 반도체 그룹만 있어야 함
        assert '반도체' in report['by_group']
        assert '자동차' not in report['by_group']


class TestIntegration:
    """통합 테스트"""
    
    def test_full_risk_workflow(self):
        """전체 리스크 관리 워크플로우"""
        # 1. 다양한 포지션 구성
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 48_000,
                'type': 'long'
            },
            {
                'ticker': '000660',
                'size': 50,
                'entry_price': 100_000,
                'stop_price': 96_000,
                'type': 'long'
            },
            {
                'ticker': '005380',
                'size': 200,
                'entry_price': 25_000,
                'stop_price': 24_500,
                'type': 'long'
            }
        ]
        
        correlation_groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        account_balance = 10_000_000
        
        # 2. 개별 포지션 리스크 계산
        for pos in positions:
            risk = calculate_position_risk(
                pos['size'],
                pos['entry_price'],
                pos['stop_price'],
                pos['type']
            )
            assert risk['total_risk'] > 0
        
        # 3. 전체 포트폴리오 리스크 계산
        portfolio_risk = calculate_total_portfolio_risk(positions, account_balance)
        assert portfolio_risk['total_risk'] > 0
        assert portfolio_risk['positions_at_risk'] == 3
        
        # 4. 리스크 한도 체크
        limits = check_risk_limits(
            portfolio_risk['total_risk'],
            account_balance,
            portfolio_risk['risk_by_ticker']
        )
        assert 'within_limits' in limits
        
        # 5. 포괄적 리포트 생성
        report = generate_risk_report(
            positions,
            account_balance,
            correlation_groups
        )
        
        assert report['summary']['total_positions'] == 3
        assert len(report['by_ticker']) == 3
        assert len(report['by_group']) == 2
        assert 'limits' in report
        assert 'warnings' in report
    
    def test_edge_case_scenarios(self):
        """극단 시나리오 테스트"""
        # 시나리오 1: 매우 큰 리스크
        positions = [
            {
                'ticker': '005930',
                'size': 100,
                'entry_price': 50_000,
                'stop_price': 30_000,  # 40% 손절
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(positions, 10_000_000)
        assert not report['summary']['within_limits']
        assert len(report['warnings']) > 0
        
        # 시나리오 2: 매우 작은 리스크
        positions = [
            {
                'ticker': '005930',
                'size': 10,
                'entry_price': 50_000,
                'stop_price': 49_900,  # 0.2% 손절
                'type': 'long'
            }
        ]
        
        report = generate_risk_report(positions, 10_000_000)
        assert report['summary']['within_limits']
        assert report['summary']['risk_percentage'] < 0.001
