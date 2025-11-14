"""
한국투자증권 API 테스트

HantuStock 클래스의 주요 기능을 테스트합니다.

실행 방법:
    # 전체 테스트 실행
    pytest src/tests/test_hantu_api.py -v
    
    # 특정 테스트만 실행
    pytest src/tests/test_hantu_api.py::test_get_access_token -v
    
    # 마커를 사용한 선택적 실행
    pytest src/tests/test_hantu_api.py -m "not slow" -v

주의사항:
    - 실제 API를 호출하므로 네트워크 연결이 필요합니다.
    - 모의투자 계정으로 테스트하는 것을 권장합니다.
    - 주문 테스트는 실제로 주문이 발생하므로 주의하세요.
"""

import pytest
import pandas as pd
from datetime import datetime


class TestHantuAPIConnection:
    """API 연결 및 인증 테스트"""
    
    def test_api_initialization(self, hantu_api):
        """API 인스턴스 초기화 테스트"""
        assert hantu_api is not None
        assert hantu_api._access_token is not None
        assert len(hantu_api._access_token) > 0
        assert hantu_api._token_issued_at is not None
        
        print(f"\n✅ API 초기화 성공")
        print(f"   Access Token: {hantu_api._access_token[:20]}...")
        print(f"   발급 시간: {hantu_api._token_issued_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def test_get_access_token_cached(self, hantu_api):
        """접근 토큰 캐싱 테스트"""
        # 첫 번째 토큰 (이미 __init__에서 발급됨)
        first_token = hantu_api._access_token
        first_issued_at = hantu_api._token_issued_at
        
        # 두 번째 호출 - 캐시된 토큰 반환 (새로 발급하지 않음)
        second_token = hantu_api.get_access_token()
        second_issued_at = hantu_api._token_issued_at
        
        # 같은 토큰이어야 함 (캐싱 확인)
        assert first_token == second_token
        assert first_issued_at == second_issued_at
        
        print(f"\n✅ 토큰 캐싱 작동 확인")
        print(f"   첫 번째 토큰: {first_token[:20]}...")
        print(f"   두 번째 토큰: {second_token[:20]}...")
        print(f"   ✓ 동일한 토큰 반환 (새로 발급하지 않음)")
    
    def test_get_token_info(self, hantu_api):
        """토큰 정보 조회 테스트"""
        token_info = hantu_api.get_token_info()
        
        assert token_info is not None
        assert 'token' in token_info
        assert 'issued_at' in token_info
        assert 'expires_in' in token_info
        assert 'remaining_time' in token_info
        
        assert token_info['token'] is not None
        assert token_info['expires_in'] == 86400  # 24시간
        assert token_info['remaining_time'] > 0
        
        print(f"\n✅ 토큰 정보 조회 성공")
        print(f"   토큰: {token_info['token']}")
        print(f"   발급 시간: {token_info['issued_at']}")
        print(f"   유효 기간: {token_info['expires_in']}초 (24시간)")
        print(f"   남은 시간: {token_info['remaining_time']:.0f}초")
    
    def test_get_header(self, hantu_api):
        """헤더 생성 테스트"""
        header = hantu_api.get_header('TTC8434R')
        
        assert 'content-type' in header
        assert 'appkey' in header
        assert 'authorization' in header
        assert 'tr_id' in header
        
        # 모드에 따른 TR ID 접두사 확인
        expected_prefix = hantu_api._tr_prefix
        assert header['tr_id'].startswith(expected_prefix)
        
        print(f"\n✅ 헤더 생성 성공")
        print(f"   TR ID: {header['tr_id']}")


class TestHantuAPIMarketData:
    """시장 데이터 조회 테스트"""
    
    def test_get_past_data_single(self, hantu_api, test_ticker):
        """단일 종목 과거 데이터 조회 (1일) 테스트"""
        data = hantu_api.get_past_data(test_ticker, n=1)
        
        assert data is not None
        assert isinstance(data, pd.Series)
        assert 'close' in data
        assert 'volume' in data
        
        print(f"\n✅ 단일 데이터 조회 성공")
        print(f"   종목: {test_ticker}")
        print(f"   종가: {data['close']:,.0f}원")
    
    def test_get_past_data_multiple(self, hantu_api, test_ticker):
        """단일 종목 과거 데이터 조회 (여러 일) 테스트"""
        n = 5
        data = hantu_api.get_past_data(test_ticker, n=n)
        
        assert data is not None
        assert isinstance(data, pd.DataFrame)
        assert len(data) == n
        
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in data.columns
        
        print(f"\n✅ 복수 데이터 조회 성공")
        print(f"   종목: {test_ticker}")
        print(f"   데이터 개수: {len(data)}일")
        print("\n   최근 3일 종가:")
        for idx, row in data.tail(3).iterrows():
            print(f"   - {row['timestamp']}: {row['close']:,.0f}원")
    
    @pytest.mark.slow
    def test_get_past_data_total(self, hantu_api):
        """전체 시장 데이터 조회 테스트 (시간 소요)"""
        n = 3  # 테스트용으로 3일만 조회
        data = hantu_api.get_past_data_total(n=n)
        
        assert data is not None
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        required_columns = ['ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in data.columns
        
        unique_dates = data['timestamp'].nunique()
        unique_tickers = data['ticker'].nunique()
        
        print(f"\n✅ 전체 시장 데이터 조회 성공")
        print(f"   총 데이터 개수: {len(data):,}건")
        print(f"   일자 수: {unique_dates}일")
        print(f"   종목 수: {unique_tickers:,}개")


class TestHantuAPIAccount:
    """계좌 정보 조회 테스트"""
    
    def test_get_holding_cash(self, hantu_api):
        """보유 현금 조회 테스트"""
        cash = hantu_api.get_holding_cash()
        
        assert cash is not None
        assert isinstance(cash, float)
        assert cash >= 0
        
        print(f"\n✅ 보유 현금 조회 성공")
        print(f"   보유 현금: {cash:,.0f}원")
    
    def test_get_holding_stock_all(self, hantu_api):
        """전체 보유 주식 조회 테스트"""
        holdings = hantu_api.get_holding_stock()
        
        assert holdings is not None
        assert isinstance(holdings, dict)
        
        print(f"\n✅ 전체 보유 주식 조회 성공")
        print(f"   보유 종목 수: {len(holdings)}개")
        
        if holdings:
            print("\n   보유 종목:")
            for ticker, quantity in list(holdings.items())[:5]:  # 최대 5개만 출력
                print(f"   - {ticker}: {quantity}주")
        else:
            print("   보유 종목이 없습니다.")
    
    def test_get_holding_stock_specific(self, hantu_api, test_ticker):
        """특정 종목 보유 수량 조회 테스트"""
        quantity = hantu_api.get_holding_stock(ticker=test_ticker)
        
        assert quantity is not None
        assert isinstance(quantity, int)
        assert quantity >= 0
        
        print(f"\n✅ 특정 종목 보유 수량 조회 성공")
        print(f"   종목: {test_ticker}")
        print(f"   보유 수량: {quantity}주")


@pytest.mark.skip(reason="실제 주문이 발생하므로 수동으로만 실행")
class TestHantuAPIOrder:
    """주문 기능 테스트 (실제 주문 발생 주의!)"""
    
    def test_bid_market_order(self, hantu_api, test_ticker):
        """시장가 매수 주문 테스트"""
        # 주의: 실제로 주문이 발생합니다!
        order_id, quantity = hantu_api.bid(
            ticker=test_ticker,
            price='market',
            quantity=10000,  # 1만원어치
            quantity_scale='CASH'
        )
        
        assert order_id is not None or quantity == 0
        
        if order_id:
            print(f"\n✅ 시장가 매수 주문 성공")
            print(f"   주문번호: {order_id}")
            print(f"   주문 수량: {quantity}주")
        else:
            print(f"\n⚠️  주문 실패 또는 수량 0")
    
    def test_ask_market_order(self, hantu_api, test_ticker):
        """시장가 매도 주문 테스트"""
        # 주의: 실제로 주문이 발생합니다!
        # 먼저 보유 수량 확인
        holding_qty = hantu_api.get_holding_stock(ticker=test_ticker)
        
        if holding_qty > 0:
            order_id, quantity = hantu_api.ask(
                ticker=test_ticker,
                price='market',
                quantity=1,
                quantity_scale='STOCK'
            )
            
            assert order_id is not None or quantity == 0
            
            if order_id:
                print(f"\n✅ 시장가 매도 주문 성공")
                print(f"   주문번호: {order_id}")
                print(f"   주문 수량: {quantity}주")
            else:
                print(f"\n⚠️  주문 실패")
        else:
            print(f"\n⚠️  보유 수량이 없어 매도 테스트를 건너뜁니다.")
            pytest.skip("보유 수량 없음")


class TestHantuAPIIntegration:
    """통합 테스트"""
    
    def test_full_workflow(self, hantu_api, test_ticker):
        """전체 워크플로우 테스트"""
        print("\n" + "="*60)
        print("📊 한국투자증권 API 통합 테스트")
        print("="*60)
        
        # 1. API 연결 확인
        print("\n1️⃣  API 연결 확인")
        assert hantu_api._access_token is not None
        token_info = hantu_api.get_token_info()
        print(f"   ✓ API 연결 성공")
        print(f"   ✓ 토큰 남은 시간: {token_info['remaining_time']:.0f}초")
        
        # 2. 계좌 정보 조회
        print("\n2️⃣  계좌 정보 조회")
        cash = hantu_api.get_holding_cash()
        holdings = hantu_api.get_holding_stock()
        print(f"   ✓ 보유 현금: {cash:,.0f}원")
        print(f"   ✓ 보유 종목 수: {len(holdings)}개")
        
        # 3. 시장 데이터 조회
        print("\n3️⃣  시장 데이터 조회")
        data = hantu_api.get_past_data(test_ticker, n=1)
        print(f"   ✓ 종목: {test_ticker}")
        print(f"   ✓ 현재가: {data['close']:,.0f}원")
        
        # 4. 특정 종목 보유 확인
        print("\n4️⃣  특정 종목 보유 확인")
        qty = hantu_api.get_holding_stock(ticker=test_ticker)
        print(f"   ✓ {test_ticker} 보유: {qty}주")
        
        print("\n" + "="*60)
        print("✅ 모든 통합 테스트 통과!")
        print("="*60)
        
        assert True


if __name__ == '__main__':
    # 직접 실행 시 pytest 호출
    pytest.main([__file__, '-v', '-s'])
