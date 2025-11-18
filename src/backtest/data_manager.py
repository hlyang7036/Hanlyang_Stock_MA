"""
백테스팅 데이터 관리 모듈

전체 시장 데이터 로딩 및 관리 기능을 제공합니다.
병렬 처리와 캐싱을 통해 효율적인 데이터 로딩을 지원합니다.
"""

import pandas as pd
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class DataManager:
    """
    백테스팅 데이터 관리 클래스

    전체 시장 데이터 로딩, 병렬 처리, 캐싱 기능을 제공합니다.

    Attributes:
        use_cache: 캐시 사용 여부
        cache_dir: 캐시 디렉토리 경로

    Methods:
        get_all_market_tickers(market): 전체 시장 종목 코드 조회
        load_market_data(start_date, end_date, market, max_workers): 전체 시장 데이터 로드
        load_data(tickers, start_date, end_date, calculate_indicators): 멀티 종목 데이터 로드
        load_cached_data(ticker, start_date, end_date): 캐시에서 데이터 로드
        cache_data(ticker, data): 데이터를 캐시에 저장
    """

    def __init__(
        self,
        use_cache: bool = False,
        cache_dir: str = 'data/cache'
    ):
        """
        데이터 관리자 초기화

        Args:
            use_cache: 캐시 사용 여부 (기본값: False)
            cache_dir: 캐시 디렉토리 경로 (기본값: 'data/cache')
        """
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir)

        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"캐시 활성화: {self.cache_dir}")

        logger.info("DataManager 초기화 완료")

    def get_all_market_tickers(
        self,
        market: str = 'ALL'
    ) -> List[str]:
        """
        전체 시장 종목 코드 조회

        Args:
            market: 시장 구분
                - 'KOSPI': 코스피만
                - 'KOSDAQ': 코스닥만
                - 'ALL': 코스피 + 코스닥 (기본값)

        Returns:
            List[str]: 종목코드 리스트

        Notes:
            - FinanceDataReader 활용
            - 상장폐지 종목 자동 제외

        Examples:
            >>> manager = DataManager()
            >>> tickers = manager.get_all_market_tickers('KOSPI')
            >>> len(tickers)
            900  # 대략적인 숫자

            >>> all_tickers = manager.get_all_market_tickers('ALL')
            >>> len(all_tickers)
            2400  # 코스피 + 코스닥
        """
        try:
            import FinanceDataReader as fdr
        except ImportError:
            raise ImportError(
                "FinanceDataReader가 설치되어 있지 않습니다. "
                "설치: pip install finance-datareader"
            )

        logger.info(f"{market} 시장 종목 코드 조회 중...")

        if market == 'KOSPI':
            df = fdr.StockListing('KOSPI')
        elif market == 'KOSDAQ':
            df = fdr.StockListing('KOSDAQ')
        elif market == 'ALL':
            kospi = fdr.StockListing('KOSPI')
            kosdaq = fdr.StockListing('KOSDAQ')
            df = pd.concat([kospi, kosdaq], ignore_index=True)
        else:
            raise ValueError(
                f"잘못된 시장 구분: {market}. "
                "'KOSPI', 'KOSDAQ', 'ALL' 중 하나를 선택하세요."
            )

        # 종목코드만 추출
        tickers = df['Code'].tolist()

        logger.info(f"{market} 시장 종목 수: {len(tickers)}개")

        return tickers

    def load_market_data(
        self,
        start_date: str,
        end_date: str,
        market: str = 'ALL',
        max_workers: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """
        전체 시장 데이터 로드 (병렬 처리)

        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
            max_workers: 병렬 처리 워커 수 (기본값: 10)

        Returns:
            Dict[str, pd.DataFrame]: {ticker: DataFrame}
                - 데이터 로딩에 실패한 종목은 제외됨
                - 각 DataFrame은 OHLCV + 지표 + 스테이지 포함

        Notes:
            - concurrent.futures.ThreadPoolExecutor 활용
            - tqdm으로 진행 상황 표시
            - 실패한 종목은 경고 로그 후 제외

        Examples:
            >>> manager = DataManager()
            >>> data = manager.load_market_data(
            ...     start_date='2020-01-01',
            ...     end_date='2023-12-31',
            ...     market='ALL'
            ... )
            >>> len(data)
            2156  # 실제 데이터가 있는 종목만 (2400개 중)
        """
        # 전체 종목 코드 조회
        tickers = self.get_all_market_tickers(market)

        logger.info(f"데이터 로딩 시작: {len(tickers)}개 종목")
        logger.info(f"기간: {start_date} ~ {end_date}")

        result = {}
        failed = []

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목별로 load_data 태스크 제출
            future_to_ticker = {
                executor.submit(
                    self.load_data,
                    [ticker],
                    start_date,
                    end_date,
                    calculate_indicators=True
                ): ticker
                for ticker in tickers
            }

            # 진행 상황 표시
            with tqdm(total=len(tickers), desc="데이터 로딩") as pbar:
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    try:
                        data_dict = future.result()
                        if ticker in data_dict and data_dict[ticker] is not None:
                            if not data_dict[ticker].empty:
                                result[ticker] = data_dict[ticker]
                            else:
                                failed.append(ticker)
                        else:
                            failed.append(ticker)
                    except Exception as e:
                        logger.warning(f"데이터 로딩 실패: {ticker} - {e}")
                        failed.append(ticker)
                    finally:
                        pbar.update(1)

        logger.info(
            f"데이터 로딩 완료: 성공 {len(result)}개, 실패 {len(failed)}개"
        )

        if failed:
            logger.debug(f"실패 종목 샘플 (최대 10개): {failed[:10]}")

        return result

    def load_data(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        calculate_indicators: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        멀티 종목 데이터 로드

        Args:
            tickers: 종목코드 리스트
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            calculate_indicators: 지표 계산 여부 (기본값: True)

        Returns:
            Dict[str, pd.DataFrame]: {ticker: DataFrame}
                각 DataFrame은 OHLCV + 지표 + 스테이지 포함

        Notes:
            - Level 1의 get_stock_data() 활용
            - Level 2의 calculate_all_indicators() 활용
            - Level 3의 determine_stage() 활용
            - 캐시가 있으면 캐시에서 로드

        Examples:
            >>> manager = DataManager()
            >>> data = manager.load_data(
            ...     ['005930', '000660'],
            ...     '2020-01-01',
            ...     '2023-12-31'
            ... )
            >>> data['005930'].columns
            Index(['Open', 'High', 'Low', 'Close', 'Volume',
                   'EMA_5', 'EMA_20', 'EMA_40', 'MACD_상', ..., 'Stage'])
        """
        from src.data.collector import get_stock_data
        from src.analysis.technical.indicators import calculate_all_indicators
        from src.analysis.stage import determine_stage, detect_stage_transition

        result = {}

        for ticker in tickers:
            try:
                # 캐시 확인
                if self.use_cache:
                    cached = self.load_cached_data(ticker, start_date, end_date)
                    if cached is not None:
                        result[ticker] = cached
                        logger.debug(f"캐시에서 로드: {ticker}")
                        continue

                # 데이터 로드
                data = get_stock_data(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date
                )

                if data is None or data.empty:
                    logger.warning(f"데이터 없음: {ticker}")
                    result[ticker] = None
                    continue

                if calculate_indicators:
                    # 지표 계산
                    data = calculate_all_indicators(data)

                    # 스테이지 분석
                    data['Stage'] = determine_stage(data)
                    data['Stage_Transition'] = detect_stage_transition(data)

                # 캐싱
                if self.use_cache:
                    self.cache_data(ticker, data, start_date, end_date)

                result[ticker] = data

            except Exception as e:
                logger.error(f"{ticker} 데이터 로드 실패: {e}")
                result[ticker] = None

        return result

    def load_cached_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        캐시에서 데이터 로드

        Args:
            ticker: 종목코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            pd.DataFrame or None: 캐시된 데이터 또는 None
        """
        if not self.use_cache:
            return None

        # 캐시 파일 경로
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.pkl"

        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                return data
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {ticker} - {e}")
                return None

        return None

    def cache_data(
        self,
        ticker: str,
        data: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> None:
        """
        데이터를 캐시에 저장

        Args:
            ticker: 종목코드
            data: 저장할 데이터
            start_date: 시작일
            end_date: 종료일
        """
        if not self.use_cache:
            return

        # 캐시 파일 경로
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {ticker} - {e}")

    def clear_cache(self) -> None:
        """
        캐시 디렉토리의 모든 캐시 파일 삭제
        """
        if not self.use_cache:
            logger.warning("캐시가 비활성화되어 있습니다.")
            return

        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob('*.pkl'))
            for cache_file in cache_files:
                cache_file.unlink()
            logger.info(f"캐시 삭제 완료: {len(cache_files)}개 파일")
        else:
            logger.info("캐시 디렉토리가 존재하지 않습니다.")

    def get_cache_info(self) -> Dict[str, any]:
        """
        캐시 정보 조회

        Returns:
            Dict: 캐시 정보
                - enabled: 캐시 사용 여부
                - directory: 캐시 디렉토리 경로
                - file_count: 캐시 파일 수
                - total_size: 총 캐시 크기 (MB)
        """
        info = {
            'enabled': self.use_cache,
            'directory': str(self.cache_dir),
            'file_count': 0,
            'total_size': 0.0
        }

        if self.use_cache and self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob('*.pkl'))
            info['file_count'] = len(cache_files)

            total_size = sum(f.stat().st_size for f in cache_files)
            info['total_size'] = total_size / (1024 * 1024)  # MB로 변환

        return info
