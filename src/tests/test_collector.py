"""
collector.py 모듈 테스트

성공 케이스에 대한 테스트만 포함합니다.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

# src 모듈 import
from src.data.collector import (
    get_stock_data,
    get_real_time_data,
    get_historical_data,
    get_multiple_stocks,
    get_current_price,
    get_market_status,
    validate_data,
    _normalize_dataframe,
)


class TestNormalizeDataFrame:
    """_normalize_dataframe 함수 테스트"""
    
    def test_normalize_fdr_format(self):
        """FinanceDataReader 형식 정규화 테스트"""
        # FDR 형식의 샘플 데이터
        df = pd.DataFrame({
            'Open': [60000, 61000, 62000],
            'High': [61000, 62000, 63000],
            'Low': [59000, 60000, 61000],
            'Close': [60500, 61500, 62500],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
        
        result = _normalize_dataframe(df, 'fdr')
        
        # 검증
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3
        assert result.index.is_monotonic_increasing  # 오름차순 정렬 확인
    
    def test_normalize_pykrx_format(self):
        """pykrx 형식 정규화 테스트"""
        # pykrx 형식의 샘플 데이터
        df = pd.DataFrame({
            '시가': [60000, 61000, 62000],
            '고가': [61000, 62000, 63000],
            '저가': [59000, 60000, 61000],
            '종가': [60500, 61500, 62500],
            '거래량': [1000000, 1100000, 1200000],
        }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
        
        result = _normalize_dataframe(df, 'pykrx')
        
        # 검증
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3


class TestValidateData:
    """validate_data 함수 테스트"""
    
    def test_validate_valid_data(self):
        """정상 데이터 검증 테스트"""
        df = pd.DataFrame({
            'Open': [60000, 61000, 62000],
            'High': [61000, 62000, 63000],
            'Low': [59000, 60000, 61000],
            'Close': [60500, 61500, 62500],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
        
        result = validate_data(df)
        assert result is True
    
    def test_validate_with_min_rows(self):
        """최소 행 수 검증 테스트"""
        df = pd.DataFrame({
            'Open': [60000, 61000, 62000, 63000, 64000],
            'High': [61000, 62000, 63000, 64000, 65000],
            'Low': [59000, 60000, 61000, 62000, 63000],
            'Close': [60500, 61500, 62500, 63500, 64500],
            'Volume': [1000000, 1100000, 1200000, 1300000, 1400000],
        }, index=pd.date_range('2024-01-01', periods=5))
        
        result = validate_data(df, min_rows=5)
        assert result is True


class TestGetHistoricalData:
    """get_historical_data 함수 테스트"""
    
    def test_get_historical_data_fdr(self):
        """FinanceDataReader로 과거 데이터 조회 테스트"""
        ticker = '005930'  # 삼성전자
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        df = get_historical_data(ticker, start_date, end_date, source='fdr')
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.is_monotonic_increasing
    
    def test_get_historical_data_pykrx(self):
        """pykrx로 과거 데이터 조회 테스트"""
        ticker = '005930'  # 삼성전자
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        df = get_historical_data(ticker, start_date, end_date, source='pykrx')
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(df.index, pd.DatetimeIndex)


class TestGetRealTimeData:
    """get_real_time_data 함수 테스트"""
    
    def test_get_real_time_data_daily(self):
        """일봉 실시간 데이터 조회 테스트"""
        ticker = '005930'  # 삼성전자
        period = 'D'
        count = 30
        
        df = get_real_time_data(ticker, period, count)
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(df.index, pd.DatetimeIndex)
        assert len(df) <= count  # count 이하여야 함


class TestGetStockData:
    """get_stock_data 함수 테스트"""
    
    def test_get_stock_data_default(self):
        """기본 사용 - 최근 50일 (FDR) 테스트"""
        ticker = '005930'
        
        df = get_stock_data(ticker)
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert isinstance(df.index, pd.DatetimeIndex)
        # 약 50일치 데이터 (영업일 기준이므로 정확히 50일은 아님)
        assert 30 <= len(df) <= 60
    
    def test_get_stock_data_with_days(self):
        """days 파라미터 - 최근 N일 테스트"""
        ticker = '005930'
        days = 30
        
        df = get_stock_data(ticker, days=days)
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
        # 약 30일치 데이터 (영업일 기준)
        assert 15 <= len(df) <= 40
    
    def test_get_stock_data_with_start_end_date(self):
        """start_date/end_date - 명시적 기간 테스트"""
        ticker = '005930'
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        df = get_stock_data(ticker, start_date=start_date, end_date=end_date)
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def test_get_stock_data_long_period(self):
        """장기 백테스팅 - FDR 자동 선택 테스트"""
        ticker = '005930'
        start_date = '2023-01-01'
        end_date = '2023-12-31'
        
        df = get_stock_data(ticker, start_date=start_date, end_date=end_date, source='auto')
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def test_get_stock_data_with_api_source(self):
        """실시간 데이터 - API 명시 테스트"""
        ticker = '005930'
        days = 30
        
        df = get_stock_data(ticker, days=days, source='api')
        
        # 검증
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def test_get_stock_data_days_and_start_date_error(self):
        """days와 start_date 동시 사용 에러 테스트"""
        ticker = '005930'
        
        with pytest.raises(ValueError, match="days와 start_date를 동시에 사용할 수 없습니다"):
            get_stock_data(ticker, days=30, start_date='2024-01-01')
    
    def test_get_stock_data_invalid_days(self):
        """잘못된 days 값 에러 테스트"""
        ticker = '005930'
        
        with pytest.raises(ValueError, match="days는 1 이상이어야 합니다"):
            get_stock_data(ticker, days=0)
        
        with pytest.raises(ValueError, match="days는 1 이상이어야 합니다"):
            get_stock_data(ticker, days=-10)


class TestGetMultipleStocks:
    """get_multiple_stocks 함수 테스트"""
    
    def test_get_multiple_stocks_success(self):
        """다종목 데이터 수집 테스트"""
        tickers = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        result = get_multiple_stocks(tickers, start_date, end_date, source='fdr')
        
        # 검증
        assert isinstance(result, dict)
        assert len(result) == len(tickers)
        
        for ticker in tickers:
            assert ticker in result
            if result[ticker] is not None:
                assert isinstance(result[ticker], pd.DataFrame)
                assert not result[ticker].empty


class TestGetCurrentPrice:
    """get_current_price 함수 테스트"""
    
    def test_get_current_price_success(self):
        """현재가 조회 테스트"""
        ticker = '005930'  # 삼성전자
        
        price = get_current_price(ticker)
        
        # 검증
        assert isinstance(price, float)
        assert price > 0


class TestGetMarketStatus:
    """get_market_status 함수 테스트"""
    
    def test_get_market_status_success(self):
        """시장 상태 확인 테스트"""
        status = get_market_status()
        
        # 검증
        assert isinstance(status, str)
        assert status in ['open', 'close', 'pre_market', 'after_hours', 'unknown']


# pytest 실행을 위한 메인
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
