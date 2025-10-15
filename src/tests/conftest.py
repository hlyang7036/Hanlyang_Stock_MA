"""
Pytest 설정 및 공통 Fixtures

한국투자증권 API 테스트를 위한 공통 설정
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_api_credentials
from src.utils.koreainvestment.HantuStock import HantuStock


@pytest.fixture(scope="session")
def api_credentials():
    """
    API 인증 정보 fixture
    
    Returns:
        dict: API 인증 정보
    """
    return get_api_credentials()


@pytest.fixture(scope="session")
def hantu_api(api_credentials):
    """
    HantuStock API 인스턴스 fixture
    
    세션 전체에서 하나의 인스턴스를 재사용합니다.
    
    Args:
        api_credentials: API 인증 정보 fixture
        
    Returns:
        HantuStock: 초기화된 API 인스턴스
    """
    api = HantuStock(
        api_key=api_credentials['api_key'],
        secret_key=api_credentials['secret_key'],
        account_id=api_credentials['account_id'],
        mode=api_credentials['mode']
    )
    return api


@pytest.fixture(scope="session")
def test_ticker():
    """
    테스트용 종목 코드 fixture
    
    Returns:
        str: 삼성전자 종목 코드
    """
    return '005930'  # 삼성전자
