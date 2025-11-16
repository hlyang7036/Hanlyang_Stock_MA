"""
포트폴리오 제한 모듈 테스트

테스트 대상:
- check_single_position_limit: 단일 종목 포지션 제한 체크
- check_correlated_group_limit: 상관관계 그룹 제한 체크
- check_diversified_limit: 분산 투자 제한 체크
- check_total_exposure_limit: 전체 포트폴리오 노출 제한 체크
- get_available_position_size: 실제 추가 가능한 포지션 크기 계산
"""

import pytest
from src.analysis.risk.portfolio import (
    check_single_position_limit,
    check_correlated_group_limit,
    check_diversified_limit,
    check_total_exposure_limit,
    get_available_position_size
)


class TestCheckSinglePositionLimit:
    """단일 종목 포지션 제한 체크 테스트"""
    
    def test_within_limit(self):
        """한도 내 - 허용"""
        result = check_single_position_limit(2, 1, 4)
        
        assert result['allowed'] is True
        assert result['available_units'] == 2
        assert result['current_units'] == 2
        assert result['limit'] == 4
        assert 'reason' not in result
    
    def test_exactly_at_limit(self):
        """정확히 한도 - 허용"""
        result = check_single_position_limit(3, 1, 4)
        
        assert result['allowed'] is True
        assert result['available_units'] == 1
    
    def test_exceeds_limit(self):
        """한도 초과 - 거부"""
        result = check_single_position_limit(3, 2, 4)
        
        assert result['allowed'] is False
        assert result['available_units'] == 1
        assert result['current_units'] == 3
        assert result['limit'] == 4
        assert '단일 종목 최대 4유닛 초과' in result['reason']
    
    def test_zero_current_units(self):
        """현재 0유닛 - 신규 진입"""
        result = check_single_position_limit(0, 2, 4)
        
        assert result['allowed'] is True
        assert result['available_units'] == 4
    
    def test_zero_additional_units(self):
        """추가 0유닛 - 항상 허용"""
        result = check_single_position_limit(3, 0, 4)
        
        assert result['allowed'] is True
        assert result['available_units'] == 1
    
    def test_already_at_max(self):
        """이미 최대 - 추가 불가"""
        result = check_single_position_limit(4, 1, 4)
        
        assert result['allowed'] is False
        assert result['available_units'] == 0
    
    def test_custom_limit(self):
        """사용자 정의 한도"""
        result = check_single_position_limit(2, 2, 3)
        
        assert result['allowed'] is False
        assert result['limit'] == 3
    
    def test_negative_current_units_raises_error(self):
        """현재 유닛 음수 - ValueError"""
        with pytest.raises(ValueError, match="현재 유닛은 음수일 수 없습니다"):
            check_single_position_limit(-1, 2, 4)
    
    def test_negative_additional_units_raises_error(self):
        """추가 유닛 음수 - ValueError"""
        with pytest.raises(ValueError, match="추가 유닛은 음수일 수 없습니다"):
            check_single_position_limit(2, -1, 4)
    
    def test_zero_limit_raises_error(self):
        """한도 0 - ValueError"""
        with pytest.raises(ValueError, match="최대 유닛은 양수여야 합니다"):
            check_single_position_limit(2, 1, 0)
    
    def test_negative_limit_raises_error(self):
        """한도 음수 - ValueError"""
        with pytest.raises(ValueError, match="최대 유닛은 양수여야 합니다"):
            check_single_position_limit(2, 1, -4)
    
    def test_invalid_current_units_type_raises_error(self):
        """잘못된 current_units 타입 - TypeError"""
        with pytest.raises(TypeError, match="current_units는 숫자여야 합니다"):
            check_single_position_limit("2", 1, 4)
    
    def test_invalid_additional_units_type_raises_error(self):
        """잘못된 additional_units 타입 - TypeError"""
        with pytest.raises(TypeError, match="additional_units는 숫자여야 합니다"):
            check_single_position_limit(2, "1", 4)


class TestCheckCorrelatedGroupLimit:
    """상관관계 그룹 제한 체크 테스트"""
    
    def test_within_group_limit(self):
        """그룹 한도 내 - 허용"""
        positions = {'005930': 3, '000660': 2}
        groups = {'반도체': ['005930', '000660']}
        
        result = check_correlated_group_limit(positions, groups, '005930', 1, 6)
        
        assert result['allowed'] is True
        assert result['available_units'] == 1
        assert result['group_name'] == '반도체'
        assert result['group_total'] == 5
        assert result['limit'] == 6
    
    def test_exactly_at_group_limit(self):
        """정확히 그룹 한도 - 허용"""
        positions = {'005930': 3, '000660': 2}
        groups = {'반도체': ['005930', '000660']}
        
        result = check_correlated_group_limit(positions, groups, '000660', 1, 6)
        
        assert result['allowed'] is True
        assert result['available_units'] == 1
    
    def test_exceeds_group_limit(self):
        """그룹 한도 초과 - 거부"""
        positions = {'005930': 3, '000660': 2}
        groups = {'반도체': ['005930', '000660']}
        
        result = check_correlated_group_limit(positions, groups, '005930', 2, 6)
        
        assert result['allowed'] is False
        assert result['available_units'] == 1
        assert result['group_name'] == '반도체'
        assert '상관관계 그룹(반도체)' in result['reason']
    
    def test_ticker_not_in_group(self):
        """그룹에 속하지 않은 종목 - 통과"""
        positions = {'005930': 3}
        groups = {'반도체': ['005930', '000660']}
        
        result = check_correlated_group_limit(positions, groups, '005380', 5, 6)
        
        assert result['allowed'] is True
        assert result['available_units'] == 6
        assert 'group_name' not in result
    
    def test_multiple_groups(self):
        """여러 그룹 - 가장 제한적인 것 적용"""
        positions = {
            '005930': 3,  # 삼성전자
            '000660': 2,  # SK하이닉스
            '005380': 2   # 현대차
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380', '000270']
        }
        
        result = check_correlated_group_limit(positions, groups, '005930', 1, 6)
        
        assert result['group_name'] == '반도체'
        assert result['group_total'] == 5
    
    def test_empty_positions(self):
        """빈 포지션 - 허용"""
        positions = {}
        groups = {'반도체': ['005930', '000660']}
        
        result = check_correlated_group_limit(positions, groups, '005930', 3, 6)
        
        assert result['allowed'] is True
        assert result['available_units'] == 6
    
    def test_ticker_in_multiple_groups(self):
        """종목이 여러 그룹에 속함 - 가장 제한적인 것"""
        positions = {'005930': 4, '000660': 1}
        groups = {
            '반도체': ['005930', '000660'],
            '대형주': ['005930', '005380']  # 삼성전자가 두 그룹에
        }
        
        result = check_correlated_group_limit(positions, groups, '005930', 1, 6)
        
        # 반도체 그룹: 4 + 1 = 5 (available: 1)
        # 대형주 그룹: 4 (available: 2)
        # 더 제한적인 반도체 그룹 적용
        assert result['allowed'] is True
        assert result['available_units'] == 1
        assert result['group_name'] == '반도체'
    
    def test_invalid_positions_type_raises_error(self):
        """잘못된 positions 타입 - TypeError"""
        with pytest.raises(TypeError, match="positions는 딕셔너리여야 합니다"):
            check_correlated_group_limit([], {}, '005930', 1, 6)
    
    def test_invalid_ticker_type_raises_error(self):
        """잘못된 ticker 타입 - TypeError"""
        with pytest.raises(TypeError, match="ticker는 문자열이어야 합니다"):
            check_correlated_group_limit({}, {}, 5930, 1, 6)


class TestCheckDiversifiedLimit:
    """분산 투자 제한 체크 테스트"""
    
    def test_within_diversified_limit(self):
        """분산 투자 한도 내 - 허용"""
        positions = {
            '005930': 3,  # 반도체
            '000660': 2,  # 반도체
            '005380': 3   # 자동차
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380', '000270']
        }
        
        result = check_diversified_limit(positions, groups, '051910', 2, 10)
        
        assert result['allowed'] is True
        assert result['available_units'] == 2
        assert result['diversified_total'] == 8
        assert result['limit'] == 10
    
    def test_exceeds_diversified_limit(self):
        """분산 투자 한도 초과 - 거부"""
        positions = {
            '005930': 3,
            '000660': 2,
            '005380': 4
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        result = check_diversified_limit(positions, groups, '051910', 2, 10)
        
        assert result['allowed'] is False
        assert result['available_units'] == 1
        assert '분산 투자 최대 10유닛 초과' in result['reason']
    
    def test_ungrouped_tickers(self):
        """그룹에 속하지 않은 종목들 포함"""
        positions = {
            '005930': 3,  # 반도체 그룹
            '000660': 2,  # 반도체 그룹
            '051910': 2,  # 미분류
            '009830': 1   # 미분류
        }
        groups = {
            '반도체': ['005930', '000660']
        }
        
        result = check_diversified_limit(positions, groups, '005380', 2, 10)
        
        # 그룹 합계(5) + 미분류(3) + 추가(2) = 10
        assert result['allowed'] is True
        assert result['diversified_total'] == 8
    
    def test_empty_correlation_groups(self):
        """빈 상관관계 그룹 - 모든 종목을 개별 계산"""
        positions = {
            '005930': 3,
            '000660': 2,
            '005380': 2
        }
        groups = {}
        
        result = check_diversified_limit(positions, groups, '051910', 2, 10)
        
        # 모든 종목이 미분류: 3 + 2 + 2 + 2 = 9
        assert result['allowed'] is True
        assert result['diversified_total'] == 7
    
    def test_invalid_additional_units_type_raises_error(self):
        """잘못된 additional_units 타입 - TypeError"""
        with pytest.raises(TypeError, match="additional_units는 숫자여야 합니다"):
            check_diversified_limit({}, {}, '005930', "2", 10)


class TestCheckTotalExposureLimit:
    """전체 포트폴리오 노출 제한 체크 테스트"""
    
    def test_within_total_limit(self):
        """전체 한도 내 - 허용"""
        positions = {
            '005930': 4,
            '000660': 3,
            '005380': 3
        }
        
        result = check_total_exposure_limit(positions, 2, 12)
        
        assert result['allowed'] is True
        assert result['available_units'] == 2
        assert result['total_units'] == 10
        assert result['limit'] == 12
    
    def test_exactly_at_total_limit(self):
        """정확히 전체 한도 - 허용"""
        positions = {
            '005930': 4,
            '000660': 3,
            '005380': 4
        }
        
        result = check_total_exposure_limit(positions, 1, 12)
        
        assert result['allowed'] is True
        assert result['available_units'] == 1
    
    def test_exceeds_total_limit(self):
        """전체 한도 초과 - 거부"""
        positions = {
            '005930': 4,
            '000660': 3,
            '005380': 4
        }
        
        result = check_total_exposure_limit(positions, 2, 12)
        
        assert result['allowed'] is False
        assert result['available_units'] == 1
        assert result['total_units'] == 11
        assert '전체 포트폴리오 최대 12유닛 초과' in result['reason']
    
    def test_empty_positions(self):
        """빈 포지션 - 전체 허용"""
        positions = {}
        
        result = check_total_exposure_limit(positions, 5, 12)
        
        assert result['allowed'] is True
        assert result['available_units'] == 12
        assert result['total_units'] == 0
    
    def test_already_at_max(self):
        """이미 최대 - 추가 불가"""
        positions = {
            '005930': 4,
            '000660': 4,
            '005380': 4
        }
        
        result = check_total_exposure_limit(positions, 1, 12)
        
        assert result['allowed'] is False
        assert result['available_units'] == 0
    
    def test_invalid_positions_type_raises_error(self):
        """잘못된 positions 타입 - TypeError"""
        with pytest.raises(TypeError, match="positions는 딕셔너리여야 합니다"):
            check_total_exposure_limit([], 2, 12)


class TestGetAvailablePositionSize:
    """실제 추가 가능한 포지션 크기 계산 테스트"""
    
    def test_all_limits_pass(self):
        """모든 제한 통과 - 전체 허용"""
        positions = {
            '005930': 2,
            '005380': 2
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380', '000270']
        }
        
        result = get_available_position_size('051910', 2, positions, groups)
        
        assert result['allowed_units'] == 2
        assert result['limiting_factor'] == 'none'
        assert all(c['allowed'] for c in result['checks'].values())
    
    def test_single_limit_restricts(self):
        """단일 종목 제한 - 가장 제한적"""
        positions = {'005930': 3}
        groups = {}
        
        result = get_available_position_size('005930', 2, positions, groups)
        
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'single'
        assert result['checks']['single']['allowed'] is False
    
    def test_correlated_limit_restricts(self):
        """상관관계 그룹 제한 - 가장 제한적"""
        positions = {
            '005930': 2,
            '000660': 3
        }
        groups = {
            '반도체': ['005930', '000660']
        }
        
        result = get_available_position_size('005930', 2, positions, groups)
        
        # 단일: 4 - 2 = 2 가능
        # 그룹: 6 - 5 = 1 가능
        # 결과: 1 유닛 (그룹 제한)
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'correlated'
    
    def test_diversified_limit_restricts(self):
        """분산 투자 제한 - 가장 제한적"""
        positions = {
            '005930': 3,
            '000660': 2,
            '005380': 4
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        result = get_available_position_size('051910', 2, positions, groups)
        
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'diversified'
    
    def test_total_limit_restricts(self):
        """전체 노출 제한 - 가장 제한적"""
        positions = {
            '005930': 4,
            '000660': 3,
            '005380': 4
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        # 분산 한도를 늘려서 전체 제한이 걸리도록
        custom_limits = {
            'single': 4,
            'correlated': 6,
            'diversified': 13,  # 전체 한도보다 크게
            'total': 12
        }
        
        result = get_available_position_size('051910', 2, positions, groups, custom_limits)
        
        # 단일: 4 - 0 = 4 가능
        # 그룹: 통과 (새 종목)
        # 분산: 13 - 11 = 2 가능
        # 전체: 12 - 11 = 1 가능 (가장 제한적!)
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'total'
    
    def test_zero_units_available(self):
        """추가 불가 - 0 유닛"""
        positions = {
            '005930': 4,
            '000660': 4,
            '005380': 4
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380']
        }
        
        # 분산 한도를 늘려서 전체 제한이 걸리도록
        custom_limits = {
            'single': 4,
            'correlated': 6,
            'diversified': 15,  # 전체보다 크게
            'total': 12
        }
        
        result = get_available_position_size('051910', 2, positions, groups, custom_limits)
        
        # 단일: 4 - 0 = 4 가능
        # 그룹: 통과 (새 종목)
        # 분산: 15 - 12 = 3 가능
        # 전체: 12 - 12 = 0 가능 (제한!)
        assert result['allowed_units'] == 0
        assert result['limiting_factor'] == 'total'
    
    def test_custom_limits(self):
        """사용자 정의 제한"""
        positions = {'005930': 2}
        groups = {}
        limits = {
            'single': 3,
            'correlated': 5,
            'diversified': 8,
            'total': 10
        }
        
        result = get_available_position_size('005930', 2, positions, groups, limits)
        
        assert result['allowed_units'] == 1
        assert result['checks']['single']['limit'] == 3
        assert result['checks']['total']['limit'] == 10
    
    def test_new_ticker(self):
        """신규 종목 - 모든 한도 체크"""
        positions = {
            '005930': 2,
            '000660': 1
        }
        groups = {
            '반도체': ['005930', '000660']
        }
        
        result = get_available_position_size('005380', 3, positions, groups)
        
        # 신규 종목이므로 단일 제한은 4유닛 전체 가능
        # 총 3 + 3 = 6 < 12 이므로 전체 제한도 통과
        assert result['allowed_units'] == 3
        assert result['limiting_factor'] == 'none'
    
    def test_multiple_restrictions(self):
        """여러 제한 동시 - 가장 작은 값"""
        positions = {
            '005930': 3,  # 단일: 1 가능
            '000660': 2,  # 그룹: 1 가능 (3+2+2=7 > 6)
            '005380': 3
        }
        groups = {
            '반도체': ['005930', '000660']
        }
        
        result = get_available_position_size('000660', 3, positions, groups)
        
        # 단일: 4 - 2 = 2 가능
        # 그룹: 6 - 5 = 1 가능
        # 총: 12 - 8 = 4 가능
        # 최소값: 1 (그룹 제한)
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'correlated'
    
    def test_invalid_ticker_type_raises_error(self):
        """잘못된 ticker 타입 - TypeError"""
        with pytest.raises(TypeError, match="ticker는 문자열이어야 합니다"):
            get_available_position_size(5930, 2, {}, {})
    
    def test_invalid_desired_units_type_raises_error(self):
        """잘못된 desired_units 타입 - TypeError"""
        with pytest.raises(TypeError, match="desired_units는 숫자여야 합니다"):
            get_available_position_size('005930', "2", {}, {})
    
    def test_negative_desired_units_raises_error(self):
        """희망 유닛 음수 - ValueError"""
        with pytest.raises(ValueError, match="희망 유닛은 음수일 수 없습니다"):
            get_available_position_size('005930', -2, {}, {})
    
    def test_invalid_limits_type_raises_error(self):
        """잘못된 limits 타입 - TypeError"""
        with pytest.raises(TypeError, match="limits는 딕셔너리여야 합니다"):
            get_available_position_size('005930', 2, {}, {}, limits=[])


class TestIntegration:
    """통합 테스트"""
    
    def test_realistic_portfolio_scenario(self):
        """현실적인 포트폴리오 시나리오"""
        # 초기 포트폴리오
        positions = {
            '005930': 3,  # 삼성전자
            '000660': 2,  # SK하이닉스
            '005380': 3   # 현대차
        }
        
        groups = {
            '반도체': ['005930', '000660', '005490'],
            '자동차': ['005380', '000270'],
            '화학': ['051910', '009830']
        }
        
        # 삼성전자 2유닛 추가 시도 (제한에 걸리도록)
        result = get_available_position_size('005930', 2, positions, groups)
        
        # 단일: 4 - 3 = 1 가능
        # 그룹: 6 - 5 = 1 가능
        # 분산: 10 - 8 = 2 가능
        # 전체: 12 - 8 = 4 가능
        # 결과: 1 유닛만 가능 (단일 또는 그룹 제한)
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] in ['single', 'correlated']
    
    def test_progressive_position_building(self):
        """점진적 포지션 구축"""
        positions = {}
        groups = {
            '반도체': ['005930', '000660']
        }
        
        # 1차: 삼성전자 2유닛
        result1 = get_available_position_size('005930', 2, positions, groups)
        assert result1['allowed_units'] == 2
        
        positions['005930'] = 2
        
        # 2차: 삼성전자 2유닛 추가
        result2 = get_available_position_size('005930', 2, positions, groups)
        assert result2['allowed_units'] == 2
        
        positions['005930'] = 4
        
        # 3차: 삼성전자 1유닛 추가 시도 (단일 제한)
        result3 = get_available_position_size('005930', 1, positions, groups)
        assert result3['allowed_units'] == 0
        assert result3['limiting_factor'] == 'single'
    
    def test_group_limit_with_multiple_tickers(self):
        """그룹 제한 - 여러 종목"""
        positions = {
            '005930': 2,
            '000660': 2,
            '005490': 1  # SK하이닉스
        }
        groups = {
            '반도체': ['005930', '000660', '005490']
        }
        
        # 그룹 합계: 5 유닛
        # SK하이닉스 2유닛 추가 시도
        result = get_available_position_size('000660', 2, positions, groups)
        
        # 단일: 4 - 2 = 2 가능
        # 그룹: 6 - 5 = 1 가능 (제한!)
        # 결과: 1 유닛만 가능
        assert result['allowed_units'] == 1
        assert result['limiting_factor'] == 'correlated'
    
    def test_max_portfolio_capacity(self):
        """최대 포트폴리오 용량"""
        positions = {
            '005930': 4,
            '000660': 3,
            '005380': 4,
            '051910': 1
        }
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380'],
            '화학': ['051910']
        }
        
        # 분산 한도를 늘려서 전체 제한이 걸리도록
        custom_limits = {
            'single': 4,
            'correlated': 6,
            'diversified': 15,
            'total': 12
        }
        
        # 총 12 유닛 → 추가 불가
        result = get_available_position_size('009830', 1, positions, groups, custom_limits)
        
        assert result['allowed_units'] == 0
        assert result['limiting_factor'] == 'total'
    
    def test_empty_to_full_portfolio(self):
        """빈 포트폴리오 → 가득 찬 포트폴리오"""
        positions = {}
        groups = {
            '반도체': ['005930', '000660'],
            '자동차': ['005380', '000270'],
            '화학': ['051910', '009830']
        }
        
        # 1. 삼성전자 4유닛 (단일 최대)
        result1 = get_available_position_size('005930', 4, positions, groups)
        assert result1['allowed_units'] == 4
        positions['005930'] = 4
        
        # 2. SK하이닉스 2유닛 (그룹 최대 6)
        result2 = get_available_position_size('000660', 2, positions, groups)
        assert result2['allowed_units'] == 2
        positions['000660'] = 2
        
        # 3. 현대차 4유닛 시도
        result3 = get_available_position_size('005380', 4, positions, groups)
        # 단일: 4 가능
        # 그룹: 6 가능 (새 그룹)
        # 분산: 10 - 6 = 4 가능
        # 전체: 12 - 6 = 6 가능
        # 결과: 4 유닛 가능
        assert result3['allowed_units'] == 4
        positions['005380'] = 4
        
        # 4. LG화학 4유닛 시도
        result4 = get_available_position_size('051910', 4, positions, groups)
        # 단일: 4 가능
        # 그룹: 6 가능 (새 그룹)
        # 분산: 10 - 10 = 0 가능 (제한!)
        # 전체: 12 - 10 = 2 가능
        # 결과: 0 유닛 (분산 제한)
        assert result4['allowed_units'] == 0
        assert result4['limiting_factor'] == 'diversified'
        
        # 대신 2유닛만 추가 (전체 제한 고려)
        result4_retry = get_available_position_size('051910', 2, positions, groups)
        # 분산: 10 - 10 = 0
        # 전체: 12 - 10 = 2
        # 여전히 분산 제한에 걸림
        assert result4_retry['allowed_units'] == 0
        
        # 분산 한도를 늘린 설정으로 재시도
        custom_limits = {
            'single': 4,
            'correlated': 6,
            'diversified': 15,  # 전체보다 크게
            'total': 12
        }
        result4_custom = get_available_position_size('051910', 2, positions, groups, custom_limits)
        # 분산: 15 - 10 = 5 가능
        # 전체: 12 - 10 = 2 가능
        # 결과: 2 유닛 가능 (전체 제한)
        assert result4_custom['allowed_units'] == 2
        positions['051910'] = 2
        
        # 5. 추가 시도 - 전체 제한 (12유닛)
        result5 = get_available_position_size('009830', 3, positions, groups, custom_limits)
        # 분산: 15 - 12 = 3 가능
        # 전체: 12 - 12 = 0 가능 (제한!)
        assert result5['allowed_units'] == 0
        assert result5['limiting_factor'] == 'total'
