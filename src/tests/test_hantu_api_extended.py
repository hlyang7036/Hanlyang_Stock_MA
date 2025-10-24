"""
HantuStock 확장 기능 테스트
- 실시간 현재가 조회
- 날짜 지정 과거 데이터 조회
- 날짜별 시장 데이터 조회
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta


class TestHantuAPIExtended:
    """HantuStock 확장 기능 테스트 클래스"""
    
    def test_get_current_price(self, hantu_api):
        """실시간 현재가 조회 테스트"""
        print("\n[테스트] 실시간 현재가 조회")
        
        # 삼성전자로 테스트
        ticker = "005930"
        result = hantu_api.get_current_price(ticker)
        
        # 결과 확인
        assert result is not None, "현재가 조회 결과가 None입니다"
        assert isinstance(result, dict), "현재가 조회 결과가 dict가 아닙니다"
        
        # 필수 필드 확인
        required_fields = ['current_price', 'prev_close', 'open', 'high', 'low', 'volume', 'change_rate', 'timestamp']
        for field in required_fields:
            assert field in result, f"필수 필드 '{field}'가 없습니다"
        
        # 가격 유효성 확인
        assert result['current_price'] > 0, "현재가가 0보다 작습니다"
        assert result['high'] >= result['low'], "고가가 저가보다 낮습니다"
        assert result['high'] >= result['current_price'] >= result['low'], "현재가가 고가/저가 범위를 벗어났습니다"
        
        print(f"✅ 현재가 조회 성공: {ticker} = {result['current_price']:,}원")
        print(f"   - 전일대비: {result['change_rate']}%")
        print(f"   - 거래량: {result['volume']:,}주")
        
    def test_get_past_data_by_date(self, hantu_api):
        """날짜 지정 과거 데이터 조회 테스트"""
        print("\n[테스트] 날짜 지정 과거 데이터 조회")
        
        # 테스트 설정
        ticker = "005930"  # 삼성전자
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 30일 전
        
        # 날짜 형식 변환
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        # 데이터 조회
        result = hantu_api.get_past_data_by_date(ticker, start_str, end_str)
        
        # 결과 확인
        assert isinstance(result, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert not result.empty, "조회된 데이터가 없습니다"
        
        # 컬럼 확인
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in expected_columns:
            assert col in result.columns, f"필수 컬럼 '{col}'이 없습니다"
        
        # 데이터 정합성 확인
        assert len(result) > 0, "데이터가 비어있습니다"
        # 각 날짜별로 고가가 저가보다 크거나 같아야 함
        assert (result['high'] >= result['low']).all(), "고가가 저가보다 낮은 데이터가 있습니다"
        # 각 날짜별로 종가가 고가 이하, 저가 이상이어야 함
        assert (result['close'] <= result['high']).all(), "종가가 고가보다 높은 데이터가 있습니다"
        assert (result['close'] >= result['low']).all(), "종가가 저가보다 낮은 데이터가 있습니다"
        
        # 날짜 순서 확인
        assert result['timestamp'].is_monotonic_increasing, "날짜가 오름차순이 아닙니다"
        
        print(f"✅ 날짜 지정 데이터 조회 성공: {len(result)}개 레코드")
        print(f"   - 기간: {result['timestamp'].min()} ~ {result['timestamp'].max()}")
        print(f"   - 시작가: {result.iloc[0]['close']:,}원")
        print(f"   - 종료가: {result.iloc[-1]['close']:,}원")
        
    def test_get_past_data_by_date_with_invalid_ticker(self, hantu_api):
        """잘못된 종목 코드로 날짜 지정 조회 테스트"""
        print("\n[테스트] 잘못된 종목 코드로 날짜 지정 조회")
        
        ticker = "999999"  # 존재하지 않는 종목
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        result = hantu_api.get_past_data_by_date(ticker, start_date, end_date)
        
        # 빈 DataFrame 반환 확인
        assert isinstance(result, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert result.empty, "존재하지 않는 종목인데 데이터가 조회되었습니다"
        
        print("✅ 잘못된 종목 처리 정상")
        
    def test_get_market_data_by_date(self, hantu_api):
        """날짜별 전체 시장 데이터 조회 테스트"""
        print("\n[테스트] 날짜별 전체 시장 데이터 조회")
        
        # 최근 평일 찾기 (주말 제외)
        test_date = datetime.now()
        while test_date.weekday() >= 5:  # 토요일(5), 일요일(6)
            test_date -= timedelta(days=1)
        
        date_str = test_date.strftime('%Y-%m-%d')
        
        # 데이터 조회
        result = hantu_api.get_market_data_by_date(date_str)
        
        # 결과 확인
        assert isinstance(result, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        
        if not result.empty:
            # 컬럼 확인
            expected_columns = ['ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in expected_columns:
                assert col in result.columns, f"필수 컬럼 '{col}'이 없습니다"
            
            # 데이터 정합성 확인
            assert result['ticker'].nunique() > 100, "종목 수가 너무 적습니다"
            assert (result['timestamp'] == pd.to_datetime(date_str)).all(), "날짜가 일치하지 않습니다"
            
            print(f"✅ 시장 데이터 조회 성공: {date_str}")
            print(f"   - 종목 수: {result['ticker'].nunique()}개")
            print(f"   - 총 거래대금: {result['trade_amount'].sum():,.0f}원")
        else:
            print(f"⚠️ {date_str}은 휴장일입니다")
            
    def test_get_market_data_by_date_weekend(self, hantu_api):
        """주말 날짜로 시장 데이터 조회 테스트"""
        print("\n[테스트] 주말 날짜로 시장 데이터 조회")
        
        # 가장 최근 토요일 찾기
        test_date = datetime.now()
        while test_date.weekday() != 5:  # 토요일
            test_date -= timedelta(days=1)
        
        date_str = test_date.strftime('%Y-%m-%d')
        
        # 데이터 조회
        result = hantu_api.get_market_data_by_date(date_str)
        
        # 주말은 빈 DataFrame 반환 확인
        assert isinstance(result, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert result.empty, f"{date_str}(토요일)인데 데이터가 조회되었습니다"
        
        print(f"✅ 주말 처리 정상: {date_str}")
        
    @pytest.mark.parametrize("ticker", ["005930", "000660", "035720"])
    def test_get_current_price_multiple(self, hantu_api, ticker):
        """여러 종목 현재가 조회 테스트"""
        result = hantu_api.get_current_price(ticker)
        
        assert result is not None, f"{ticker} 현재가 조회 실패"
        assert result['current_price'] > 0, f"{ticker} 현재가가 0 이하"
        
        print(f"✅ {ticker}: {result['current_price']:,}원 (전일대비 {result['change_rate']}%)")


class TestDataIntegrity:
    """데이터 정합성 테스트"""
    
    def test_price_consistency_between_methods(self, hantu_api):
        """서로 다른 메서드 간 가격 일관성 테스트"""
        print("\n[테스트] 메서드 간 가격 일관성 확인")
        
        ticker = "005930"
        
        # 1. 현재가 조회
        current_data = hantu_api.get_current_price(ticker)
        assert current_data is not None, "현재가 조회 실패"
        
        # 2. get_past_data로 최근 1일 조회
        past_data = hantu_api.get_past_data(ticker, n=1)
        
        # Series를 DataFrame으로 변환
        if isinstance(past_data, pd.Series):
            past_close = past_data.get('close', past_data.get('Close', 0))
        else:
            past_close = past_data.iloc[-1]['close'] if not past_data.empty else 0
        
        # 3. 날짜 지정 조회로 오늘 데이터
        today = datetime.now().strftime('%Y%m%d')
        yesterday = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        date_data = hantu_api.get_past_data_by_date(ticker, yesterday, today)
        
        print(f"✅ 가격 데이터 비교:")
        print(f"   - 현재가 API: {current_data['current_price']:,}원")
        print(f"   - get_past_data: {past_close:,}원")
        if not date_data.empty:
            print(f"   - 날짜지정 API: {date_data.iloc[-1]['close']:,}원")
        
        # 현재가와 과거 데이터의 차이가 10% 이내인지 확인 (장중 변동 고려)
        if past_close > 0:
            price_diff = abs(current_data['current_price'] - past_close) / past_close * 100
            assert price_diff < 10, f"현재가와 과거 데이터 차이가 너무 큽니다: {price_diff:.2f}%"
