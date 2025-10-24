"""
데이터 수집 모듈
- 실시간 데이터 조회
- 과거 데이터 조회  
- 전체 시장 데이터 조회
- 백테스트와 실거래 전략에서 공통으로 사용
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
from ...config.config_loader import get_api_credentials
from ...utils.koreainvestment.HantuStock import HantuStock


class DataCollector:
    """주식 데이터 수집 클래스"""
    
    def __init__(self, mode: str = 'simulation'):
        """
        DataCollector 초기화
        
        Args:
            mode (str): 거래 모드 ('simulation' 또는 'real')
        """
        self.mode = mode
        self._hantu = None
        self._cache = {}  # 간단한 메모리 캐시
        
    @property
    def hantu(self) -> HantuStock:
        """HantuStock 인스턴스 (지연 초기화)"""
        if self._hantu is None:
            creds = get_api_credentials()
            self._hantu = HantuStock(
                api_key=creds['api_key'],
                secret_key=creds['secret_key'],
                account_id=creds['account_id'],
                mode=self.mode
            )
        return self._hantu
        
    # =====================================================================
    # 실시간 데이터 조회
    # =====================================================================
    
    def get_realtime_data(self, ticker: str) -> Optional[Dict]:
        """
        실시간 주식 데이터 조회
        
        Args:
            ticker (str): 종목 코드
            
        Returns:
            dict: 실시간 데이터 {
                'ticker': 종목코드,
                'current_price': 현재가,
                'prev_close': 전일종가,
                'open': 시가,
                'high': 고가,
                'low': 저가,
                'volume': 거래량,
                'change_rate': 등락률,
                'timestamp': 조회시간
            } or None
        """
        try:
            # HantuStock의 현재가 조회 메서드 활용
            price_data = self.hantu.get_current_price(ticker)
            
            if price_data:
                # 종목 코드 추가
                price_data['ticker'] = ticker
                return price_data
            else:
                print(f"❌ {ticker}: 실시간 데이터 조회 실패")
                return None
                
        except Exception as e:
            print(f"❌ {ticker}: 실시간 데이터 조회 오류 - {e}")
            return None
    
    def get_realtime_data_bulk(self, tickers: List[str]) -> pd.DataFrame:
        """
        여러 종목의 실시간 데이터 일괄 조회
        
        Args:
            tickers (List[str]): 종목 코드 리스트
            
        Returns:
            DataFrame: 실시간 데이터
        """
        data_list = []
        
        for ticker in tickers:
            data = self.get_realtime_data(ticker)
            if data:
                data_list.append(data)
                
        if data_list:
            df = pd.DataFrame(data_list)
            return df
        else:
            return pd.DataFrame()
    
    # =====================================================================
    # 과거 데이터 조회
    # =====================================================================
    
    def get_historical_data(self, 
                          ticker: str, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          n_days: Optional[int] = None) -> pd.DataFrame:
        """
        과거 주식 데이터 조회 (유연한 인터페이스)
        
        Args:
            ticker (str): 종목 코드
            start_date (str, optional): 시작일 (YYYY-MM-DD)
            end_date (str, optional): 종료일 (YYYY-MM-DD)
            n_days (int, optional): 최근 n일
            
        Returns:
            DataFrame: 과거 데이터
        """
        # 캐시 확인
        cache_key = f"{ticker}_{start_date}_{end_date}_{n_days}"
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        try:
            # n_days가 지정된 경우
            if n_days is not None:
                result = self.hantu.get_past_data(ticker, n=n_days)
                
                # Series를 DataFrame으로 변환
                if isinstance(result, pd.Series):
                    result = result.to_frame().T
                    
            # 날짜 범위가 지정된 경우
            elif start_date is not None:
                # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
                start_str = start_date.replace('-', '') if '-' in str(start_date) else str(start_date)
                end_str = end_date.replace('-', '') if end_date and '-' in str(end_date) else end_date
                
                result = self.hantu.get_past_data_by_date(ticker, start_str, end_str)
                
            else:
                # 기본값: 최근 100일
                result = self.hantu.get_past_data(ticker, n=100)
                if isinstance(result, pd.Series):
                    result = result.to_frame().T
            
            # 데이터 표준화
            result = self._standardize_data(result)
            
            # 캐시에 저장 (최대 100개)
            if len(self._cache) > 100:
                self._cache.popitem()  # FIFO
            self._cache[cache_key] = result.copy()
            
            return result
            
        except Exception as e:
            print(f"❌ {ticker}: 과거 데이터 조회 오류 - {e}")
            return pd.DataFrame()
    
    def get_historical_data_for_backtest(self, 
                                       ticker: str,
                                       target_date: str,
                                       lookback_days: int = 100) -> pd.DataFrame:
        """
        백테스트용 과거 데이터 조회 (특정 날짜 기준)
        
        Args:
            ticker (str): 종목 코드
            target_date (str): 기준 날짜 (YYYY-MM-DD)
            lookback_days (int): 과거 조회 일수
            
        Returns:
            DataFrame: target_date 이전 lookback_days 기간의 데이터
        """
        try:
            # 날짜 계산
            target_dt = pd.to_datetime(target_date)
            start_dt = target_dt - timedelta(days=lookback_days * 2)  # 여유있게
            
            # 데이터 조회
            data = self.get_historical_data(
                ticker,
                start_date=start_dt.strftime('%Y-%m-%d'),
                end_date=target_date
            )
            
            if not data.empty:
                # target_date 이전 데이터만 필터링
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data = data[data['timestamp'] <= target_dt]
                
                # 최근 lookback_days개만 반환
                return data.tail(lookback_days).copy()
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ {ticker}: 백테스트 데이터 조회 오류 - {e}")
            return pd.DataFrame()
    
    # =====================================================================
    # 시장 데이터 조회
    # =====================================================================
    
    def get_market_data(self, date: Optional[str] = None, n_days: Optional[int] = None) -> pd.DataFrame:
        """
        전체 시장 데이터 조회
        
        Args:
            date (str, optional): 특정 날짜 (YYYY-MM-DD)
            n_days (int, optional): 최근 n일
            
        Returns:
            DataFrame: 시장 데이터
        """
        try:
            # 특정 날짜 조회
            if date is not None:
                return self.hantu.get_market_data_by_date(date)
                
            # 최근 n일 조회
            elif n_days is not None:
                return self.hantu.get_past_data_total(n=n_days)
                
            # 기본값: 최근 20일
            else:
                return self.hantu.get_past_data_total(n=20)
                
        except Exception as e:
            print(f"❌ 시장 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def get_market_data_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        날짜 범위의 전체 시장 데이터 조회
        
        Args:
            start_date (str): 시작일 (YYYY-MM-DD)
            end_date (str): 종료일 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 기간별 시장 데이터
        """
        try:
            all_data = []
            current_date = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            while current_date <= end_dt:
                if current_date.weekday() < 5:  # 평일만
                    date_str = current_date.strftime('%Y-%m-%d')
                    daily_data = self.get_market_data(date=date_str)
                    
                    if not daily_data.empty:
                        all_data.append(daily_data)
                        
                current_date += timedelta(days=1)
                
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                return result.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 날짜 범위 시장 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    # =====================================================================
    # 계좌 정보 조회
    # =====================================================================
    
    def get_account_info(self) -> Dict:
        """
        계좌 정보 조회
        
        Returns:
            dict: {
                'cash': 현금 잔고,
                'holdings': {ticker: quantity} 보유 종목
            }
        """
        try:
            cash = self.hantu.get_holding_cash()
            holdings = self.hantu.get_holding_stock()
            
            return {
                'cash': cash,
                'holdings': holdings
            }
        except Exception as e:
            print(f"❌ 계좌 정보 조회 오류: {e}")
            return {'cash': 0, 'holdings': {}}
    
    # =====================================================================
    # 유틸리티 메서드
    # =====================================================================
    
    def _standardize_data(self, data: Union[pd.DataFrame, pd.Series]) -> pd.DataFrame:
        """
        데이터 표준화
        
        Args:
            data: 원본 데이터
            
        Returns:
            DataFrame: 표준화된 데이터
        """
        if isinstance(data, pd.Series):
            data = data.to_frame().T
            
        if isinstance(data, pd.DataFrame) and not data.empty:
            # 컬럼명 표준화
            data.columns = [col.lower() for col in data.columns]
            
            # timestamp 컬럼 확인
            if 'timestamp' not in data.columns:
                if data.index.name in ['timestamp', 'date']:
                    data = data.reset_index()
                    data.rename(columns={data.columns[0]: 'timestamp'}, inplace=True)
                else:
                    # 임시로 현재 시간 추가
                    data['timestamp'] = datetime.now()
                    
            # timestamp를 datetime으로 변환
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
        return data
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        print("✅ 데이터 캐시 초기화 완료")
        
    def get_cache_stats(self) -> Dict:
        """캐시 상태 조회"""
        total_size = sum(df.memory_usage(deep=True).sum() for df in self._cache.values())
        return {
            'items': len(self._cache),
            'memory_mb': total_size / 1024 / 1024,
            'keys': list(self._cache.keys())[:10]  # 최대 10개만
        }


# 전역 인스턴스 (싱글톤 패턴)
_collector_instance = None

def get_data_collector(mode: str = 'simulation') -> DataCollector:
    """
    DataCollector 인스턴스 반환 (싱글톤)
    
    Args:
        mode (str): 거래 모드
        
    Returns:
        DataCollector: 데이터 수집기 인스턴스
    """
    global _collector_instance
    if _collector_instance is None or _collector_instance.mode != mode:
        _collector_instance = DataCollector(mode)
    return _collector_instance
