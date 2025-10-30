"""
주가 데이터 수집 모듈

이 모듈은 실시간 데이터와 과거 데이터를 수집하고 정규화하는 기능을 제공합니다.
strategy와 backtest 모두에서 사용되는 공통 데이터 수집 인터페이스입니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로거 설정
logger = logging.getLogger(__name__)


def _normalize_dataframe(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    다양한 소스의 DataFrame을 표준 형식으로 정규화합니다.
    
    표준 형식:
    - Index: datetime 타입
    - Columns: Open, High, Low, Close, Volume (대문자 시작)
    - 정렬: 날짜 오름차순
    - 결측치 제거
    
    Args:
        df: 원본 DataFrame
        source: 데이터 출처 ('api', 'fdr', 'pykrx')
    
    Returns:
        정규화된 DataFrame
    
    Raises:
        ValueError: 필수 컬럼이 없는 경우
    """
    if df is None or df.empty:
        raise ValueError("DataFrame이 비어있습니다.")
    
    df = df.copy()
    
    # 소스별 컬럼명 매핑
    column_mapping = {
        'api': {
            'stck_oprc': 'Open',
            'stck_hgpr': 'High',
            'stck_lwpr': 'Low',
            'stck_clpr': 'Close',
            'acml_vol': 'Volume',
        },
        'fdr': {
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
        },
        'pykrx': {
            '시가': 'Open',
            '고가': 'High',
            '저가': 'Low',
            '종가': 'Close',
            '거래량': 'Volume',
        }
    }
    
    # 컬럼명 변경
    if source in column_mapping:
        mapping = column_mapping[source]
        # 존재하는 컬럼만 매핑
        rename_dict = {old: new for old, new in mapping.items() if old in df.columns}
        df = df.rename(columns=rename_dict)
    
    # 필수 컬럼 확인
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    # 필수 컬럼만 선택
    df = df[required_columns]
    
    # 데이터 타입 변환
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').astype('int64')
    
    # 인덱스를 datetime으로 변환
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            logger.error(f"날짜 인덱스 변환 실패: {e}")
            raise
    
    # 날짜 오름차순 정렬
    df = df.sort_index()
    
    # 결측치 제거
    df = df.dropna()
    
    # 중복 제거 (같은 날짜의 중복 데이터)
    df = df[~df.index.duplicated(keep='last')]
    
    return df


def validate_data(df: pd.DataFrame, min_rows: int = 1) -> bool:
    """
    수집된 데이터의 유효성을 검증합니다.
    
    검증 항목:
    - 필수 컬럼 존재 여부
    - 최소 데이터 개수
    - 가격 데이터 이상치 (음수, 0)
    - High >= Low 검증
    
    Args:
        df: 검증할 DataFrame
        min_rows: 최소 필요 행 수 (기본값: 1)
    
    Returns:
        유효하면 True, 아니면 False
    """
    try:
        # 빈 데이터 확인
        if df is None or df.empty:
            logger.warning("데이터가 비어있습니다.")
            return False
        
        # 최소 행 수 확인
        if len(df) < min_rows:
            logger.warning(f"데이터 개수 부족: {len(df)} < {min_rows}")
            return False
        
        # 필수 컬럼 확인
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            logger.warning("필수 컬럼이 없습니다.")
            return False
        
        # 가격 데이터 이상치 확인 (음수 또는 0)
        price_columns = ['Open', 'High', 'Low', 'Close']
        for col in price_columns:
            if (df[col] <= 0).any():
                logger.warning(f"{col} 컬럼에 0 이하의 값이 있습니다.")
                return False
        
        # High >= Low 검증
        if (df['High'] < df['Low']).any():
            logger.warning("High가 Low보다 작은 데이터가 있습니다.")
            return False
        
        # Volume 음수 확인
        if (df['Volume'] < 0).any():
            logger.warning("Volume에 음수 값이 있습니다.")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"데이터 검증 중 오류 발생: {e}")
        return False


def get_historical_data(
    ticker: str,
    start_date: str,
    end_date: str = None,
    source: str = 'fdr'
) -> pd.DataFrame:
    """
    과거 장기간 데이터를 조회합니다 (백테스팅용).
    
    Args:
        ticker: 종목 코드 (예: '005930')
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD), None이면 오늘
        source: 데이터 소스 ('fdr' 또는 'pykrx')
    
    Returns:
        정규화된 DataFrame (OHLCV)
    
    Raises:
        ValueError: 잘못된 파라미터
        Exception: 데이터 수집 실패
    
    Examples:
        >>> df = get_historical_data('005930', '2020-01-01', '2023-12-31')
        >>> print(df.head())
    """
    if not ticker:
        raise ValueError("종목 코드를 입력해주세요.")
    
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"과거 데이터 수집: {ticker} ({start_date} ~ {end_date}) from {source}")
    
    try:
        if source == 'fdr':
            import FinanceDataReader as fdr
            df = fdr.DataReader(ticker, start_date, end_date)
            
        elif source == 'pykrx':
            from pykrx import stock
            # 날짜 형식 변환 (YYYYMMDD)
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            df = stock.get_market_ohlcv_by_date(start, end, ticker)
            
        else:
            raise ValueError(f"지원하지 않는 소스: {source}")
        
        # 데이터 정규화
        df = _normalize_dataframe(df, source)
        
        # 데이터 검증
        if not validate_data(df):
            raise ValueError("수집된 데이터가 유효하지 않습니다.")
        
        logger.info(f"데이터 수집 완료: {len(df)}개 행")
        return df
        
    except Exception as e:
        logger.error(f"과거 데이터 수집 실패: {e}")
        raise


def get_real_time_data(
    ticker: str,
    period: str = 'D',
    count: int = 100
) -> pd.DataFrame:
    """
    HantuStock API를 사용하여 최근 N일 데이터를 조회합니다.
    
    Args:
        ticker: 종목 코드 (예: '005930')
        period: 봉 주기 ('D'=일봉, '1'=1분봉, '5'=5분봉 등)
        count: 조회할 데이터 개수
    
    Returns:
        정규화된 DataFrame (OHLCV)
    
    Raises:
        ValueError: 잘못된 파라미터
        Exception: API 호출 실패
    
    Examples:
        >>> df = get_real_time_data('005930', 'D', 100)
        >>> print(df.tail())
    """
    if not ticker:
        raise ValueError("종목 코드를 입력해주세요.")
    
    if count <= 0:
        raise ValueError("count는 1 이상이어야 합니다.")
    
    logger.info(f"실시간 데이터 수집: {ticker} (기간: {period}, 개수: {count})")
    
    try:
        # HantuStock API import
        from src.utils.koreainvestment import HantuStock
        from src.config.config_loader import get_api_credentials
        
        # API 인증 정보 가져오기
        credentials = get_api_credentials()
        
        # API 인스턴스 생성
        api = HantuStock(
            api_key=credentials['api_key'],
            secret_key=credentials['secret_key'],
            account_id=credentials['account_id'],
            mode=credentials['mode']
        )
        
        # 일봉 데이터 조회
        if period == 'D':
            df = api.inquire_daily_price(ticker, adj_price=True)
            if df is not None and not df.empty:
                # 최근 count개만 선택
                df = df.tail(count)
        else:
            # 분봉 데이터는 추후 구현
            raise NotImplementedError(f"'{period}' 봉은 아직 지원하지 않습니다.")
        
        if df is None or df.empty:
            raise ValueError("데이터 수집 실패: 빈 데이터")
        
        # 데이터 정규화
        df = _normalize_dataframe(df, 'api')
        
        # 데이터 검증
        if not validate_data(df):
            raise ValueError("수집된 데이터가 유효하지 않습니다.")
        
        logger.info(f"데이터 수집 완료: {len(df)}개 행")
        return df
        
    except Exception as e:
        logger.error(f"실시간 데이터 수집 실패: {e}")
        raise


def get_stock_data(
    ticker: str,
    start_date: str = None,
    end_date: str = None,
    period: str = 'D',
    source: str = 'auto'
) -> pd.DataFrame:
    """
    주가 데이터를 수집하는 통합 인터페이스입니다.
    
    source='auto'일 때 날짜 범위에 따라 자동으로 소스를 선택합니다:
    - 최근 100일 이내: HantuStock API 사용
    - 그 이상: FinanceDataReader 사용
    
    Args:
        ticker: 종목 코드 (예: '005930')
        start_date: 시작일 (YYYY-MM-DD), None이면 100일 전
        end_date: 종료일 (YYYY-MM-DD), None이면 오늘
        period: 봉 주기 ('D'=일봉)
        source: 데이터 소스 ('auto', 'api', 'fdr', 'pykrx')
    
    Returns:
        정규화된 DataFrame (OHLCV)
    
    Raises:
        ValueError: 잘못된 파라미터
        Exception: 데이터 수집 실패
    
    Examples:
        >>> # 자동 선택 (최근 100일)
        >>> df = get_stock_data('005930')
        
        >>> # 과거 데이터
        >>> df = get_stock_data('005930', '2020-01-01', '2023-12-31')
        
        >>> # 특정 소스 지정
        >>> df = get_stock_data('005930', source='fdr')
    """
    if not ticker:
        raise ValueError("종목 코드를 입력해주세요.")
    
    # 기본값 설정
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if start_date is None:
        # 기본값: 100일 전
        start = datetime.now() - timedelta(days=100)
        start_date = start.strftime('%Y-%m-%d')
    
    logger.info(f"데이터 수집 시작: {ticker} ({start_date} ~ {end_date})")
    
    try:
        # 소스 자동 선택
        if source == 'auto':
            # 날짜 차이 계산
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days_diff = (end_dt - start_dt).days
            
            # 100일 이내면 API, 이상이면 FDR
            if days_diff <= 100:
                source = 'api'
                logger.info("자동 선택: API (최근 100일 이내)")
            else:
                source = 'fdr'
                logger.info("자동 선택: FinanceDataReader (100일 초과)")
        
        # 소스별 데이터 수집
        if source == 'api':
            # 날짜 차이 계산하여 count 결정
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            count = max((end_dt - start_dt).days + 10, 100)  # 여유있게
            
            df = get_real_time_data(ticker, period, count)
            
            # 날짜 범위 필터링
            df = df.loc[start_date:end_date]
            
        elif source in ['fdr', 'pykrx']:
            df = get_historical_data(ticker, start_date, end_date, source)
            
        else:
            raise ValueError(f"지원하지 않는 소스: {source}")
        
        logger.info(f"데이터 수집 완료: {len(df)}개 행")
        return df
        
    except Exception as e:
        logger.error(f"데이터 수집 실패: {e}")
        raise


def get_multiple_stocks(
    tickers: List[str],
    start_date: str = None,
    end_date: str = None,
    **kwargs
) -> Dict[str, pd.DataFrame]:
    """
    여러 종목의 데이터를 병렬로 수집합니다.
    
    Args:
        tickers: 종목 코드 리스트
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        **kwargs: get_stock_data()에 전달할 추가 파라미터
    
    Returns:
        {ticker: DataFrame} 딕셔너리
    
    Examples:
        >>> tickers = ['005930', '000660', '035420']
        >>> data = get_multiple_stocks(tickers, '2023-01-01', '2023-12-31')
        >>> for ticker, df in data.items():
        ...     print(f"{ticker}: {len(df)} rows")
    """
    if not tickers:
        raise ValueError("종목 코드 리스트를 입력해주세요.")
    
    logger.info(f"다종목 데이터 수집 시작: {len(tickers)}개 종목")
    
    result = {}
    
    # 병렬 처리
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 작업 제출
        future_to_ticker = {
            executor.submit(get_stock_data, ticker, start_date, end_date, **kwargs): ticker
            for ticker in tickers
        }
        
        # 결과 수집
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                df = future.result()
                result[ticker] = df
                logger.info(f"{ticker} 수집 완료: {len(df)}개 행")
            except Exception as e:
                logger.error(f"{ticker} 수집 실패: {e}")
                result[ticker] = None
    
    logger.info(f"다종목 데이터 수집 완료: {len(result)}개 종목")
    return result


def get_current_price(ticker: str) -> float:
    """
    특정 종목의 현재가를 조회합니다.
    
    Args:
        ticker: 종목 코드 (예: '005930')
    
    Returns:
        현재가 (float)
    
    Raises:
        Exception: 조회 실패
    
    Examples:
        >>> price = get_current_price('005930')
        >>> print(f"현재가: {price:,.0f}원")
    """
    if not ticker:
        raise ValueError("종목 코드를 입력해주세요.")
    
    try:
        # HantuStock API import
        from src.utils.koreainvestment import HantuStock
        from src.config.config_loader import get_api_credentials
        
        # API 인증 정보 가져오기
        credentials = get_api_credentials()
        
        # API 인스턴스 생성
        api = HantuStock(
            api_key=credentials['api_key'],
            secret_key=credentials['secret_key'],
            account_id=credentials['account_id'],
            mode=credentials['mode']
        )
        
        # 현재가 조회
        price = api.inquire_price(ticker)
        
        if price is None:
            raise ValueError("현재가 조회 실패")
        
        return float(price)
        
    except Exception as e:
        logger.error(f"현재가 조회 실패: {e}")
        raise


def get_market_status() -> str:
    """
    현재 시장 상태를 확인합니다.
    
    Returns:
        시장 상태 ('open', 'close', 'pre_market', 'after_hours')
    
    Examples:
        >>> status = get_market_status()
        >>> if status == 'open':
        ...     print("장이 열려있습니다.")
    """
    try:
        now = datetime.now()
        current_time = now.time()
        
        # 주말 확인
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return 'close'
        
        # 시간대별 상태
        from datetime import time
        
        pre_market_start = time(8, 30)
        market_open = time(9, 0)
        market_close = time(15, 30)
        after_hours_end = time(18, 0)
        
        if pre_market_start <= current_time < market_open:
            return 'pre_market'
        elif market_open <= current_time < market_close:
            return 'open'
        elif market_close <= current_time < after_hours_end:
            return 'after_hours'
        else:
            return 'close'
        
    except Exception as e:
        logger.error(f"시장 상태 확인 실패: {e}")
        return 'unknown'
