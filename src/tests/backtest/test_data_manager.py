"""
데이터 관리 모듈 테스트
"""

import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.backtest.data_manager import DataManager


class TestDataManager:
    """DataManager 클래스 테스트"""

    def test_manager_creation_no_cache(self):
        """캐시 없이 매니저 생성 테스트"""
        manager = DataManager(use_cache=False)

        assert manager.use_cache is False
        assert manager.cache_dir == Path('data/cache')

    def test_manager_creation_with_cache(self):
        """캐시 활성화하여 매니저 생성 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataManager(
                use_cache=True,
                cache_dir=tmpdir
            )

            assert manager.use_cache is True
            assert manager.cache_dir == Path(tmpdir)
            assert manager.cache_dir.exists()

    @patch('FinanceDataReader.StockListing')
    def test_get_all_market_tickers_kospi(self, mock_stock_listing):
        """KOSPI 종목 코드 조회 테스트"""
        # Mock 데이터 설정
        mock_df = pd.DataFrame({
            'Code': ['005930', '000660', '035420'],
            'Name': ['삼성전자', 'SK하이닉스', 'NAVER']
        })
        mock_stock_listing.return_value = mock_df

        manager = DataManager()
        tickers = manager.get_all_market_tickers('KOSPI')

        assert len(tickers) == 3
        assert '005930' in tickers
        assert '000660' in tickers
        assert '035420' in tickers

    @patch('FinanceDataReader.StockListing')
    def test_get_all_market_tickers_kosdaq(self, mock_stock_listing):
        """KOSDAQ 종목 코드 조회 테스트"""
        # Mock 데이터 설정
        mock_df = pd.DataFrame({
            'Code': ['035720', '122870'],
            'Name': ['카카오', '엔에스쇼핑']
        })
        mock_stock_listing.return_value = mock_df

        manager = DataManager()
        tickers = manager.get_all_market_tickers('KOSDAQ')

        assert len(tickers) == 2
        assert '035720' in tickers

    @patch('FinanceDataReader.StockListing')
    def test_get_all_market_tickers_all(self, mock_stock_listing):
        """전체 시장 종목 코드 조회 테스트"""
        # Mock 데이터 설정
        kospi_df = pd.DataFrame({
            'Code': ['005930', '000660'],
            'Name': ['삼성전자', 'SK하이닉스']
        })
        kosdaq_df = pd.DataFrame({
            'Code': ['035720', '122870'],
            'Name': ['카카오', '엔에스쇼핑']
        })

        mock_stock_listing.side_effect = [kospi_df, kosdaq_df]

        manager = DataManager()
        tickers = manager.get_all_market_tickers('ALL')

        assert len(tickers) == 4
        assert '005930' in tickers
        assert '035720' in tickers

    def test_get_all_market_tickers_invalid_market(self):
        """잘못된 시장 구분 테스트"""
        manager = DataManager()

        with pytest.raises(ValueError, match="잘못된 시장 구분"):
            manager.get_all_market_tickers('INVALID')

    def test_load_data_single_ticker(self):
        """단일 종목 데이터 로드 테스트"""
        manager = DataManager(use_cache=False)

        # 실제 데이터 로드 (삼성전자, 3개월)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '2024-01-01'

        data = manager.load_data(
            tickers=['005930'],
            start_date=start_date,
            end_date=end_date,
            calculate_indicators=True
        )

        assert '005930' in data
        assert data['005930'] is not None
        assert not data['005930'].empty

        # 필수 컬럼 확인
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            assert col in data['005930'].columns

        # 지표 컬럼 확인
        indicator_columns = ['EMA_5', 'EMA_20', 'EMA_40', 'MACD_상', 'Stage']
        for col in indicator_columns:
            assert col in data['005930'].columns

    def test_load_data_multiple_tickers(self):
        """다중 종목 데이터 로드 테스트"""
        manager = DataManager(use_cache=False)

        # 실제 데이터 로드 (2개 종목, 3개월)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '2024-08-01'

        data = manager.load_data(
            tickers=['005930', '000660'],
            start_date=start_date,
            end_date=end_date,
            calculate_indicators=True
        )

        assert '005930' in data
        assert '000660' in data
        assert data['005930'] is not None
        assert data['000660'] is not None

    def test_load_data_without_indicators(self):
        """지표 계산 없이 데이터 로드 테스트"""
        manager = DataManager(use_cache=False)

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '2024-08-01'

        data = manager.load_data(
            tickers=['005930'],
            start_date=start_date,
            end_date=end_date,
            calculate_indicators=False
        )

        assert '005930' in data
        assert data['005930'] is not None

        # 기본 컬럼만 있어야 함
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            assert col in data['005930'].columns

        # 지표 컬럼은 없어야 함
        indicator_columns = ['EMA_5', 'EMA_20', 'EMA_40', 'MACD_상']
        for col in indicator_columns:
            assert col not in data['005930'].columns

    def test_cache_data_and_load(self):
        """데이터 캐싱 및 로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataManager(
                use_cache=True,
                cache_dir=tmpdir
            )

            # 테스트 데이터 생성
            test_data = pd.DataFrame({
                'Open': [50000, 51000],
                'High': [51000, 52000],
                'Low': [49000, 50000],
                'Close': [50500, 51500],
                'Volume': [1000000, 1100000]
            })

            # 캐시 저장
            manager.cache_data(
                ticker='005930',
                data=test_data,
                start_date='2024-01-01',
                end_date='2024-01-31'
            )

            # 캐시 로드
            loaded = manager.load_cached_data(
                ticker='005930',
                start_date='2024-01-01',
                end_date='2024-01-31'
            )

            assert loaded is not None
            assert len(loaded) == 2
            assert loaded['Close'].iloc[0] == 50500

    def test_cache_disabled(self):
        """캐시 비활성화 시 테스트"""
        manager = DataManager(use_cache=False)

        # 테스트 데이터
        test_data = pd.DataFrame({
            'Open': [50000],
            'High': [51000],
            'Low': [49000],
            'Close': [50500],
            'Volume': [1000000]
        })

        # 캐시 저장 시도 (아무 일도 일어나지 않아야 함)
        manager.cache_data(
            ticker='005930',
            data=test_data,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        # 캐시 로드 시도 (None 반환해야 함)
        loaded = manager.load_cached_data(
            ticker='005930',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        assert loaded is None

    def test_clear_cache(self):
        """캐시 삭제 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataManager(
                use_cache=True,
                cache_dir=tmpdir
            )

            # 테스트 데이터 생성 및 캐싱
            test_data = pd.DataFrame({
                'Open': [50000],
                'High': [51000],
                'Low': [49000],
                'Close': [50500],
                'Volume': [1000000]
            })

            manager.cache_data('005930', test_data, '2024-01-01', '2024-01-31')
            manager.cache_data('000660', test_data, '2024-01-01', '2024-01-31')

            # 캐시 파일 확인
            cache_files = list(manager.cache_dir.glob('*.pkl'))
            assert len(cache_files) == 2

            # 캐시 삭제
            manager.clear_cache()

            # 삭제 확인
            cache_files = list(manager.cache_dir.glob('*.pkl'))
            assert len(cache_files) == 0

    def test_get_cache_info_disabled(self):
        """캐시 비활성화 시 정보 조회 테스트"""
        manager = DataManager(use_cache=False)

        info = manager.get_cache_info()

        assert info['enabled'] is False
        assert info['file_count'] == 0
        assert info['total_size'] == 0.0

    def test_get_cache_info_enabled(self):
        """캐시 활성화 시 정보 조회 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataManager(
                use_cache=True,
                cache_dir=tmpdir
            )

            # 테스트 데이터 캐싱
            test_data = pd.DataFrame({
                'Open': [50000],
                'High': [51000],
                'Low': [49000],
                'Close': [50500],
                'Volume': [1000000]
            })

            manager.cache_data('005930', test_data, '2024-01-01', '2024-01-31')

            info = manager.get_cache_info()

            assert info['enabled'] is True
            assert info['file_count'] == 1
            assert info['total_size'] > 0.0

    @patch('src.backtest.data_manager.DataManager.get_all_market_tickers')
    @patch('src.backtest.data_manager.DataManager.load_data')
    def test_load_market_data_small(self, mock_load_data, mock_get_tickers):
        """소규모 시장 데이터 로드 테스트 (Mock 사용)"""
        # Mock 설정
        mock_get_tickers.return_value = ['005930', '000660', '035420']

        # Mock load_data 반환값
        def mock_load_data_func(tickers, start_date, end_date, calculate_indicators):
            result = {}
            for ticker in tickers:
                if ticker == '005930':
                    result[ticker] = pd.DataFrame({
                        'Open': [50000],
                        'Close': [50500],
                        'Volume': [1000000]
                    })
                elif ticker == '000660':
                    result[ticker] = pd.DataFrame({
                        'Open': [80000],
                        'Close': [80500],
                        'Volume': [500000]
                    })
                else:
                    result[ticker] = None  # 실패 시뮬레이션
            return result

        mock_load_data.side_effect = mock_load_data_func

        manager = DataManager(use_cache=False)

        # 시장 데이터 로드
        data = manager.load_market_data(
            start_date='2024-01-01',
            end_date='2024-01-31',
            market='ALL',
            max_workers=2
        )

        # 성공한 2개 종목만 있어야 함
        assert len(data) == 2
        assert '005930' in data
        assert '000660' in data
        assert '035420' not in data  # 실패한 종목

    def test_load_market_data_integration(self):
        """실제 시장 데이터 로드 통합 테스트 (소규모)"""
        # 실제 API를 사용하되, 소수 종목만 테스트
        with patch('src.backtest.data_manager.DataManager.get_all_market_tickers') as mock_get_tickers:
            # 테스트용으로 2개 종목만 반환
            mock_get_tickers.return_value = ['005930', '000660']

            manager = DataManager(use_cache=False)

            data = manager.load_market_data(
                start_date='2024-08-01',
                end_date=datetime.now().strftime('%Y-%m-%d'),
                market='ALL',
                max_workers=2
            )

            # 최소 1개 종목은 성공해야 함
            assert len(data) > 0

            # 성공한 종목은 데이터가 있어야 함
            for ticker, df in data.items():
                assert df is not None
                assert not df.empty
                assert 'Open' in df.columns
                assert 'Close' in df.columns

    def test_load_data_with_cache_integration(self):
        """캐시 사용 통합 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataManager(
                use_cache=True,
                cache_dir=tmpdir
            )

            # 첫 번째 로드 (캐시 미사용)
            data1 = manager.load_data(
                tickers=['005930'],
                start_date='2024-08-01',
                end_date=datetime.now().strftime('%Y-%m-%d'),
                calculate_indicators=True
            )

            assert '005930' in data1

            # 캐시 파일 확인
            cache_files = list(manager.cache_dir.glob('*.pkl'))
            assert len(cache_files) == 1

            # 두 번째 로드 (캐시 사용)
            data2 = manager.load_data(
                tickers=['005930'],
                start_date='2024-08-01',
                end_date=datetime.now().strftime('%Y-%m-%d'),
                calculate_indicators=True
            )

            assert '005930' in data2

            # 데이터가 동일해야 함
            assert len(data1['005930']) == len(data2['005930'])

    def test_load_data_invalid_ticker(self):
        """존재하지 않는 종목 코드 테스트"""
        manager = DataManager(use_cache=False)

        data = manager.load_data(
            tickers=['999999'],  # 존재하지 않는 종목
            start_date='2024-08-01',
            end_date=datetime.now().strftime('%Y-%m-%d'),
            calculate_indicators=False
        )

        # 로드 실패 시 None 반환
        assert '999999' in data
        assert data['999999'] is None
