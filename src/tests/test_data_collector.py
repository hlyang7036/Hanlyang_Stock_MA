"""
DataCollector 모듈 테스트
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.analysis.data.data_collector import DataCollector, get_data_collector


class TestDataCollector:
    """DataCollector 기본 기능 테스트"""
    
    @pytest.fixture
    def collector(self):
        """DataCollector 인스턴스"""
        return DataCollector(mode='simulation')
    
    def test_initialization(self, collector):
        """초기화 테스트"""
        assert collector.mode == 'simulation'
        assert collector._cache == {}
        print("✅ DataCollector 초기화 성공")
    
    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        collector1 = get_data_collector('simulation')
        collector2 = get_data_collector('simulation')
        
        assert collector1 is collector2, "같은 모드에서는 동일한 인스턴스여야 합니다"
        
        collector3 = get_data_collector('real')
        assert collector3 is not collector1, "다른 모드에서는 다른 인스턴스여야 합니다"
        
        print("✅ 싱글톤 패턴 정상 작동")
    
    def test_get_realtime_data(self, collector):
        """실시간 데이터 조회 테스트"""
        print("\n[테스트] 실시간 데이터 조회")
        
        ticker = "005930"  # 삼성전자
        data = collector.get_realtime_data(ticker)
        
        assert data is not None, "실시간 데이터가 None입니다"
        assert isinstance(data, dict), "실시간 데이터가 dict가 아닙니다"
        assert data['ticker'] == ticker, "종목 코드가 일치하지 않습니다"
        assert data['current_price'] > 0, "현재가가 0 이하입니다"
        
        print(f"✅ {ticker} 실시간 데이터 조회 성공: {data['current_price']:,}원")
    
    def test_get_realtime_data_bulk(self, collector):
        """여러 종목 실시간 데이터 일괄 조회 테스트"""
        print("\n[테스트] 여러 종목 실시간 데이터 일괄 조회")
        
        tickers = ["005930", "000660", "035720"]  # 삼성전자, SK하이닉스, 카카오
        df = collector.get_realtime_data_bulk(tickers)
        
        assert isinstance(df, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert len(df) > 0, "조회된 데이터가 없습니다"
        assert set(df['ticker'].unique()) <= set(tickers), "요청하지 않은 종목이 포함되었습니다"
        
        print(f"✅ {len(df)}개 종목 실시간 데이터 조회 성공")
        for _, row in df.iterrows():
            print(f"   - {row['ticker']}: {row['current_price']:,}원 ({row['change_rate']:+.2f}%)")
    
    def test_get_historical_data_with_n_days(self, collector):
        """n일 과거 데이터 조회 테스트"""
        print("\n[테스트] n일 과거 데이터 조회")
        
        ticker = "005930"
        n_days = 30
        df = collector.get_historical_data(ticker, n_days=n_days)
        
        assert isinstance(df, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert not df.empty, "조회된 데이터가 없습니다"
        assert 'timestamp' in df.columns, "timestamp 컬럼이 없습니다"
        assert len(df) <= n_days, f"요청한 {n_days}일보다 많은 데이터가 조회되었습니다"
        
        print(f"✅ {ticker} 최근 {len(df)}일 데이터 조회 성공")
        print(f"   - 기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    def test_get_historical_data_with_date_range(self, collector):
        """날짜 범위 과거 데이터 조회 테스트"""
        print("\n[테스트] 날짜 범위 과거 데이터 조회")
        
        ticker = "005930"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        df = collector.get_historical_data(
            ticker,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        assert isinstance(df, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        assert not df.empty, "조회된 데이터가 없습니다"
        
        # 날짜 범위 확인
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        assert df['timestamp'].min() >= start_date - timedelta(days=7), "시작일이 너무 이릅니다"
        assert df['timestamp'].max() <= end_date + timedelta(days=1), "종료일이 너무 늦습니다"
        
        print(f"✅ {ticker} 날짜 범위 데이터 조회 성공: {len(df)}개")
    
    def test_get_historical_data_for_backtest(self, collector):
        """백테스트용 데이터 조회 테스트"""
        print("\n[테스트] 백테스트용 데이터 조회")
        
        ticker = "005930"
        target_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        lookback_days = 20
        
        df = collector.get_historical_data_for_backtest(ticker, target_date, lookback_days)
        
        assert isinstance(df, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        if not df.empty:
            # target_date 이전 데이터만 있는지 확인
            assert (df['timestamp'] <= pd.to_datetime(target_date)).all(), \
                "target_date 이후 데이터가 포함되었습니다"
            assert len(df) <= lookback_days, f"요청한 {lookback_days}일보다 많습니다"
            
            print(f"✅ 백테스트 데이터 조회 성공: {len(df)}개")
            print(f"   - 대상일: {target_date}")
            print(f"   - 데이터: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    def test_cache_functionality(self, collector):
        """캐시 기능 테스트"""
        print("\n[테스트] 캐시 기능")
        
        ticker = "005930"
        
        # 첫 번째 조회 (캐시 미스)
        import time
        start_time = time.time()
        df1 = collector.get_historical_data(ticker, n_days=10)
        first_call_time = time.time() - start_time
        
        # 두 번째 조회 (캐시 히트)
        start_time = time.time()
        df2 = collector.get_historical_data(ticker, n_days=10)
        second_call_time = time.time() - start_time
        
        # 캐시 효과 확인
        assert pd.DataFrame.equals(df1, df2), "캐시된 데이터가 다릅니다"
        assert second_call_time < first_call_time, "캐시가 작동하지 않습니다"
        
        # 캐시 상태 확인
        stats = collector.get_cache_stats()
        assert stats['items'] > 0, "캐시에 아이템이 없습니다"
        
        print(f"✅ 캐시 작동 확인")
        print(f"   - 첫 번째 조회: {first_call_time:.3f}초")
        print(f"   - 두 번째 조회: {second_call_time:.3f}초 (캐시)")
        print(f"   - 캐시 아이템: {stats['items']}개, {stats['memory_mb']:.2f}MB")
        
        # 캐시 초기화
        collector.clear_cache()
        stats = collector.get_cache_stats()
        assert stats['items'] == 0, "캐시가 초기화되지 않았습니다"
        print("✅ 캐시 초기화 성공")
    
    def test_get_market_data(self, collector):
        """시장 데이터 조회 테스트"""
        print("\n[테스트] 시장 데이터 조회")
        
        # 최근 5일 시장 데이터
        df = collector.get_market_data(n_days=5)
        
        assert isinstance(df, pd.DataFrame), "결과가 DataFrame이 아닙니다"
        if not df.empty:
            assert 'ticker' in df.columns, "ticker 컬럼이 없습니다"
            assert 'timestamp' in df.columns, "timestamp 컬럼이 없습니다"
            
            n_tickers = df['ticker'].nunique()
            n_dates = df['timestamp'].nunique()
            
            print(f"✅ 시장 데이터 조회 성공")
            print(f"   - 종목 수: {n_tickers}개")
            print(f"   - 날짜 수: {n_dates}일")
            print(f"   - 총 레코드: {len(df)}개")
    
    def test_get_account_info(self, collector):
        """계좌 정보 조회 테스트"""
        print("\n[테스트] 계좌 정보 조회")
        
        info = collector.get_account_info()
        
        assert isinstance(info, dict), "계좌 정보가 dict가 아닙니다"
        assert 'cash' in info, "cash 정보가 없습니다"
        assert 'holdings' in info, "holdings 정보가 없습니다"
        assert isinstance(info['holdings'], dict), "holdings가 dict가 아닙니다"
        
        print(f"✅ 계좌 정보 조회 성공")
        print(f"   - 현금: {info['cash']:,.0f}원")
        print(f"   - 보유 종목: {len(info['holdings'])}개")
        
        if info['holdings']:
            for ticker, qty in list(info['holdings'].items())[:3]:
                print(f"     • {ticker}: {qty}주")


class TestDataIntegration:
    """통합 테스트"""
    
    def test_realtime_and_historical_consistency(self):
        """실시간과 과거 데이터 일관성 테스트"""
        print("\n[통합테스트] 실시간/과거 데이터 일관성")
        
        collector = get_data_collector('simulation')
        ticker = "005930"
        
        # 실시간 데이터
        realtime = collector.get_realtime_data(ticker)
        
        # 과거 1일 데이터
        historical = collector.get_historical_data(ticker, n_days=1)
        
        if realtime and not historical.empty:
            # 가격 차이 확인 (10% 이내)
            realtime_price = realtime['current_price']
            historical_price = historical.iloc[-1]['close']
            
            price_diff = abs(realtime_price - historical_price) / historical_price * 100
            
            print(f"✅ 데이터 일관성 확인")
            print(f"   - 실시간: {realtime_price:,}원")
            print(f"   - 과거(종가): {historical_price:,}원")
            print(f"   - 차이: {price_diff:.2f}%")
            
            assert price_diff < 10, f"가격 차이가 너무 큽니다: {price_diff:.2f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
