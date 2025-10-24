"""
한국투자증권 Open API 연동 클래스

주요 기능:
- 접근 토큰 발급 및 관리
- 시장 데이터 조회 (과거 데이터, 전체 시장 데이터)
- 계좌 정보 조회 (보유 주식, 보유 현금)
- 주문 기능 (매수/매도, 시장가/지정가)
"""

import pandas as pd
import time
import requests
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import FinanceDataReader as fdr
from pykrx import stock as pystock


class HantuStock:
    """한국투자증권 Open API 연동 클래스"""
    
    def __init__(self, api_key, secret_key, account_id, mode='simulation'):
        """
        HantuStock 클래스 초기화
        
        Args:
            api_key (str): API Key
            secret_key (str): Secret Key
            account_id (str): 계좌번호
            mode (str): 거래 모드 ('simulation' 또는 'real')
        """
        self._api_key = api_key
        self._secret_key = secret_key
        self._account_id = account_id
        self._mode = mode
        
        # 모드에 따른 URL 및 TR ID 접두사 설정
        if mode == 'real':
            self._base_url = 'https://openapi.koreainvestment.com:9443'
            self._tr_prefix = 'T'  # 실거래 TR ID 접두사
            print("🔴 실거래 모드로 초기화됩니다!")
        else:
            self._base_url = 'https://openapivts.koreainvestment.com:29443'
            self._tr_prefix = 'V'  # 모의투자 TR ID 접두사
            print("🟢 모의투자 모드로 초기화됩니다.")
            
        self._account_suffix = '01'
        
        # 토큰 캐싱을 위한 변수
        self._access_token = None
        self._token_issued_at = None
        self._token_expires_in = 86400  # 24시간 (초 단위)
        
        # 초기 토큰 발급
        self._access_token = self.get_access_token()

    # =====================================================================
    # 접근 토큰 및 헤더 관리
    # =====================================================================
    
    def get_access_token(self, force_refresh=False):
        """
        OAuth2 접근 토큰 발급 (캐싱 지원)
        
        한국투자증권 API 정책:
        - 접근토큰 유효기간: 24시간
        - 토큰 발급 요청 제한: 10초에 1회
        
        Args:
            force_refresh (bool): True일 경우 기존 토큰 무시하고 강제로 새 토큰 발급
            
        Returns:
            str: 접근 토큰
        """
        # 기존 토큰이 유효한지 확인
        if not force_refresh and self._access_token and self._token_issued_at:
            token_age = datetime.now() - self._token_issued_at
            # 토큰이 23시간 이내면 재사용 (여유있게 1시간 전에 갱신)
            if token_age < timedelta(seconds=self._token_expires_in - 3600):
                return self._access_token
        
        # 새 토큰 발급
        while True:
            try:
                headers = {"content-type": "application/json"}
                body = {
                    "grant_type": "client_credentials",
                    "appkey": self._api_key, 
                    "appsecret": self._secret_key,
                }
                url = self._base_url + '/oauth2/tokenP'
                res = requests.post(url, headers=headers, data=json.dumps(body)).json()
                
                # 토큰 발급 성공
                self._access_token = res['access_token']
                self._token_issued_at = datetime.now()
                
                return self._access_token
                
            except KeyError as e:
                # 'access_token' 키가 없는 경우 - API 제한에 걸림
                print(f'⚠️  토큰 발급 제한: 10초 대기 후 재시도... (에러: {e})')
                time.sleep(10)
            except Exception as e:
                print(f'ERROR: get_access_token error. Retrying in 10 seconds...: {e}')
                time.sleep(10)
    
    def get_token_info(self):
        """
        현재 토큰 정보 조회
        
        Returns:
            dict: 토큰 정보 (token, issued_at, expires_in, remaining_time)
        """
        if not self._access_token or not self._token_issued_at:
            return {
                'token': None,
                'issued_at': None,
                'expires_in': self._token_expires_in,
                'remaining_time': None
            }
        
        token_age = datetime.now() - self._token_issued_at
        remaining_time = self._token_expires_in - token_age.total_seconds()
        
        return {
            'token': self._access_token[:20] + '...' if self._access_token else None,
            'issued_at': self._token_issued_at.strftime('%Y-%m-%d %H:%M:%S'),
            'expires_in': self._token_expires_in,
            'remaining_time': max(0, remaining_time)
        }
                
    def get_header(self, tr_id_suffix):
        """
        API 요청 헤더 생성
        
        Args:
            tr_id_suffix (str): TR ID 접미사
            
        Returns:
            dict: 요청 헤더
        """
        # TR ID를 모드에 따라 동적으로 생성 (V/T + suffix)
        tr_id = f"{self._tr_prefix}{tr_id_suffix}"
        headers = {
            "content-type": "application/json",
            "appkey": self._api_key, 
            "appsecret": self._secret_key,
            "authorization": f"Bearer {self._access_token}",
            "tr_id": tr_id,
        }
        return headers

    def _requests(self, url, headers, params, request_type='get'):
        """
        API 요청 공통 처리 함수
        
        Args:
            url (str): 요청 URL
            headers (dict): 요청 헤더
            params (dict): 요청 파라미터
            request_type (str): 요청 타입 ('get' 또는 'post')
            
        Returns:
            tuple: (응답 헤더, 응답 내용)
        """
        while True:
            try:
                if request_type == 'get':
                    response = requests.get(url, headers=headers, params=params)
                else:
                    response = requests.post(url, headers=headers, data=json.dumps(params))
                    
                returning_headers = response.headers
                contents = response.json()
                
                if contents['rt_cd'] != '0':
                    # 초당 거래건수 초과 에러 처리
                    if contents['msg_cd'] == 'EGW00201':
                        time.sleep(0.1)
                        continue
                    else:
                        print(f"ERROR at _requests: {contents}, headers: {headers}, params: {params}")
                break
                
            except requests.exceptions.SSLError as e:
                print(f'SSLERROR: {e}')
                time.sleep(0.1)
            except Exception as e:
                print(f'other _requests error: {e}')
                time.sleep(0.1)
                
        return returning_headers, contents

    # =====================================================================
    # 시장 데이터 조회
    # =====================================================================
    
    def get_past_data(self, ticker, n=100):
        """
        특정 종목의 과거 데이터 조회
        
        Args:
            ticker (str): 종목 코드
            n (int): 조회할 데이터 개수
            
        Returns:
            DataFrame: 과거 데이터 (n > 1) 또는 Series (n == 1)
        """
        temp = fdr.DataReader(ticker)
        temp.columns = list(map(lambda x: str.lower(x), temp.columns))
        temp.index.name = 'timestamp'
        temp = temp.reset_index()
        
        if n == 1:
            temp = temp.iloc[-1]
        else:
            temp = temp.tail(n)

        return temp
    
    def get_past_data_total(self, n=10):
        """
        전체 시장 과거 데이터 조회 (KOSPI + KOSDAQ)
        
        Args:
            n (int): 조회할 일수
            
        Returns:
            DataFrame: 전체 시장 과거 데이터
        """
        total_data = None
        days_passed = 0
        days_collected = 0
        today_timestamp = datetime.now()
        
        # 하루씩 돌아가면서 데이터 받아오기
        while (days_collected < n) and days_passed < max(10, n * 2):
            iter_date = str(today_timestamp - relativedelta(days=days_passed)).split(' ')[0]
            data1 = pystock.get_market_ohlcv(iter_date, market='KOSPI')
            data2 = pystock.get_market_ohlcv(iter_date, market='KOSDAQ')
            data = pd.concat([data1, data2])

            days_passed += 1
            
            # 주말일 경우 패스
            if data['거래대금'].sum() == 0:
                continue
            else:
                days_collected += 1
                
            # 안전한 컬럼명 매핑
            column_mapping = {
                '시가': 'open',
                '고가': 'high',
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume',
                '거래대금': 'trade_amount',
                '등락률': 'diff',
                '시가총액': 'market_cap'
            }

            data = data.rename(columns=column_mapping)
            data.index.name = 'ticker'
            data['timestamp'] = iter_date
            
            if total_data is None:
                total_data = data.copy()
            else:
                total_data = pd.concat([total_data, data])

        total_data = total_data.sort_values('timestamp').reset_index()

        # 거래가 없었던 종목은(거래정지) open/high/low가 0으로 표시됨
        # 이런 경우, open/high/low를 close값으로 바꿔줌
        total_data['open'] = total_data['open'].where(total_data['open'] > 0, other=total_data['close'])
        total_data['high'] = total_data['high'].where(total_data['high'] > 0, other=total_data['close'])
        total_data['low'] = total_data['low'].where(total_data['low'] > 0, other=total_data['close'])

        return total_data

    # =====================================================================
    # 계좌 정보 조회
    # =====================================================================
    
    def get_holding_stock(self, ticker=None, remove_stock_warrant=True):
        """
        보유 주식 조회
        
        Args:
            ticker (str, optional): 종목 코드. None이면 전체 보유 종목 조회
            remove_stock_warrant (bool): 신주인수권 제외 여부
            
        Returns:
            int or dict: 보유 수량 (ticker 지정 시) 또는 전체 보유 종목 딕셔너리
        """
        order_result = self._get_order_result(get_account_info=False)

        if ticker is not None:
            for order in order_result:
                if order['pdno'] == ticker:
                    return int(order['hldg_qty'])
            return 0
        else:
            returning_result = {}
            for order in order_result:
                order_tkr = order['pdno']
                # 신주인수권 제외
                if remove_stock_warrant and order_tkr[0] == 'J':
                    continue
                returning_result[order_tkr] = int(order['hldg_qty'])
            return returning_result

    def _get_order_result(self, get_account_info=False):
        """
        계좌 잔고 조회 (내부 함수)
        
        Args:
            get_account_info (bool): True일 경우 계좌 정보 반환
            
        Returns:
            list or dict: 보유 종목 리스트 또는 계좌 정보
        """
        headers = self.get_header('TTC8434R')
        output1_result = []
        cont = True
        ctx_area_fk100 = ''
        ctx_area_nk100 = ''
        
        while cont:
            params = {
                "CANO": self._account_id,
                "ACNT_PRDT_CD": self._account_suffix,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "N",
                "INQR_DVSN": "01",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": ctx_area_fk100,
                "CTX_AREA_NK100": ctx_area_nk100
            }

            url = self._base_url + '/uapi/domestic-stock/v1/trading/inquire-balance'
            hd, order_result = self._requests(url, headers, params)
            
            if get_account_info:
                return order_result['output2'][0]
            else:
                cont = hd['tr_cont'] in ['F', 'M']
                headers['tr_cont'] = 'N'
                ctx_area_fk100 = order_result['ctx_area_fk100']
                ctx_area_nk100 = order_result['ctx_area_nk100']
                output1_result = output1_result + order_result['output1']

        return output1_result

    def get_holding_cash(self):
        """
        보유 현금 조회
        
        Returns:
            float: 보유 현금 (예수금)
        """
        order_result = self._get_order_result(get_account_info=True)
        return float(order_result['prvs_rcdl_excc_amt'])

    # =====================================================================
    # 주문 기능
    # =====================================================================
    
    def bid(self, ticker, price, quantity, quantity_scale):
        """
        매수 주문
        
        Args:
            ticker (str): 종목 코드
            price (int or str): 주문 가격. 'market' 또는 0이면 시장가, 숫자면 지정가
            quantity (int or float): 주문 수량
            quantity_scale (str): 수량 단위 ('CASH' 또는 'STOCK')
            
        Returns:
            tuple: (주문번호, 실제 주문 수량)
        """
        if price in ['market', '', 0]:
            # 시장가주문
            price = '0'
            ord_dvsn = '01'
            if quantity_scale == 'CASH':
                price_for_quantity_calculation = self.get_past_data(ticker).iloc[-1]['close']
        else:
            # 지정가주문
            price_for_quantity_calculation = price
            price = str(price)
            ord_dvsn = '00'
            
        if quantity_scale == 'CASH':
            quantity = int(quantity / price_for_quantity_calculation)
        elif quantity_scale == 'STOCK':
            quantity = int(quantity)
        else:
            print('ERROR: quantity_scale should be one of CASH, STOCK')
            return None, 0

        headers = self.get_header('TTC0012U')
        params = {
            "CANO": self._account_id,
            "ACNT_PRDT_CD": self._account_suffix,
            'PDNO': ticker,
            'ORD_DVSN': ord_dvsn,
            'ORD_QTY': str(quantity),
            'ORD_UNPR': str(price)
        }

        url = self._base_url + '/uapi/domestic-stock/v1/trading/order-cash'
        hd, order_result = self._requests(url, headers=headers, params=params, request_type='post')
        
        if order_result['rt_cd'] == '0':
            return order_result['output']['ODNO'], quantity
        else:
            print(order_result['msg1'])
            return None, 0

    def ask(self, ticker, price, quantity, quantity_scale):
        """
        매도 주문
        
        Args:
            ticker (str): 종목 코드
            price (int or str): 주문 가격. 'market' 또는 0이면 시장가, 숫자면 지정가
            quantity (int or float): 주문 수량
            quantity_scale (str): 수량 단위 ('CASH' 또는 'STOCK')
            
        Returns:
            tuple: (주문번호, 실제 주문 수량)
        """
        if price in ['market', '', 0]:
            # 시장가주문
            price = '0'
            ord_dvsn = '01'
            if quantity_scale == 'CASH':
                price_for_quantity_calculation = self.get_past_data(ticker).iloc[-1]['close']
        else:
            # 지정가주문
            price_for_quantity_calculation = price
            price = str(price)
            ord_dvsn = '00'
            
        if quantity_scale == 'CASH':
            quantity = int(quantity / price_for_quantity_calculation)
        elif quantity_scale == 'STOCK':
            quantity = int(quantity)
        else:
            print('ERROR: quantity_scale should be one of CASH, STOCK')
            return None, 0

        headers = self.get_header('TTC0011U')
        params = {
            "CANO": self._account_id,
            "ACNT_PRDT_CD": self._account_suffix,
            'PDNO': ticker,
            'ORD_DVSN': ord_dvsn,
            'ORD_QTY': str(quantity),
            'ORD_UNPR': str(price)
        }
        
        url = self._base_url + '/uapi/domestic-stock/v1/trading/order-cash'
        hd, order_result = self._requests(url, headers, params, 'post')

        if order_result['rt_cd'] == '0':
            if order_result['output']['ODNO'] is None:
                print('ask error', order_result['msg1'])
                return None, 0
            return order_result['output']['ODNO'], quantity
        else:
            print(order_result['msg1'])
            return None, 0

    # =====================================================================
    # 추가 기능 - 실시간 및 날짜 지정 데이터 조회
    # =====================================================================
    
    def get_current_price(self, ticker):
        """
        실시간 현재가 조회 (다양한 방법 시도)
        
        Args:
            ticker (str): 종목 코드
            
        Returns:
            dict: 현재가 정보 {
                'current_price': 현재가,
                'prev_close': 전일종가,
                'open': 시가,
                'high': 고가,
                'low': 저가,
                'volume': 거래량,
                'change_rate': 등락률,
                'timestamp': 시간
            } or None (실패시)
        """
        try:
            # 방법 1: 기존 get_past_data 활용 (가장 안정적)
            try:
                data = self.get_past_data(ticker, n=1)
                
                if isinstance(data, pd.Series):
                    # Series인 경우
                    return {
                        'current_price': float(data.get('close', 0)),
                        'prev_close': float(data.get('close', 0)),  # 당일 종가로 대체
                        'open': float(data.get('open', 0)),
                        'high': float(data.get('high', 0)),
                        'low': float(data.get('low', 0)),
                        'volume': int(data.get('volume', 0)),
                        'change_rate': float(data.get('change', 0)) if 'change' in data else 0.0,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                elif isinstance(data, pd.DataFrame) and not data.empty:
                    # DataFrame인 경우
                    row = data.iloc[-1]
                    return {
                        'current_price': float(row.get('close', 0)),
                        'prev_close': float(row.get('close', 0)),  # 당일 종가로 대체
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'volume': int(row.get('volume', 0)),
                        'change_rate': float(row.get('change', 0)) if 'change' in row else 0.0,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            except Exception as e:
                print(f"⚠️ get_past_data 방식 실패: {e}")
            
            # 방법 2: pykrx로 당일 데이터 조회
            try:
                today = datetime.now().strftime('%Y%m%d')
                
                # KOSPI 시도
                try:
                    data = pystock.get_market_ohlcv_by_ticker(today, market='KOSPI')
                    if ticker in data.index:
                        row = data.loc[ticker]
                        return {
                            'current_price': float(row['종가']),
                            'prev_close': float(row['종가']),  # 전일 종가는 별도 조회 필요
                            'open': float(row['시가']),
                            'high': float(row['고가']),
                            'low': float(row['저가']),
                            'volume': int(row['거래량']),
                            'change_rate': float(row['등락률']),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                except:
                    pass
                
                # KOSDAQ 시도
                try:
                    data = pystock.get_market_ohlcv_by_ticker(today, market='KOSDAQ')
                    if ticker in data.index:
                        row = data.loc[ticker]
                        return {
                            'current_price': float(row['종가']),
                            'prev_close': float(row['종가']),
                            'open': float(row['시가']),
                            'high': float(row['고가']),
                            'low': float(row['저가']),
                            'volume': int(row['거래량']),
                            'change_rate': float(row['등락률']),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠️ pykrx 방식 실패: {e}")
            
            print(f"❌ {ticker}: 모든 방식으로 현재가 조회 실패")
            return None
                
        except Exception as e:
            print(f"❌ {ticker} 현재가 조회 오류: {e}")
            return None
    
    def get_past_data_by_date(self, ticker, start_date, end_date=None):
        """
        날짜 지정 과거 데이터 조회 (pykrx 우선 사용)
        
        Args:
            ticker (str): 종목 코드
            start_date (str): 시작일 (YYYYMMDD 또는 YYYY-MM-DD)
            end_date (str, optional): 종료일. None이면 오늘까지
            
        Returns:
            DataFrame: 지정된 기간의 일봉 데이터 or 빈 DataFrame (실패시)
        """
        try:
            # 날짜 형식 변환
            if '-' in str(start_date):
                start_date = start_date.replace('-', '')
            if end_date and '-' in str(end_date):
                end_date = end_date.replace('-', '')
            elif end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 방법 1: pykrx 사용 (모의투자에서도 안정적)
            # KOSPI 시도
            try:
                data = pystock.get_market_ohlcv(start_date, end_date, ticker, market='KOSPI')
                if not data.empty:
                    data = self._standardize_pykrx_data(data)
                    return data
            except:
                pass
                
            # KOSDAQ 시도
            try:
                data = pystock.get_market_ohlcv(start_date, end_date, ticker, market='KOSDAQ')
                if not data.empty:
                    data = self._standardize_pykrx_data(data)
                    return data
            except:
                pass
            
            # 방법 2: FinanceDataReader 사용
            try:
                # 전체 데이터 받아서 기간 필터링
                data = fdr.DataReader(ticker)
                if not data.empty:
                    data.columns = [col.lower() for col in data.columns]
                    data.index.name = 'timestamp'
                    data = data.reset_index()
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    
                    # 날짜 형식 변환
                    start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                    end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                    
                    # 기간 필터링
                    mask = (data['timestamp'] >= start_dt) & (data['timestamp'] <= end_dt)
                    data = data[mask].copy()
                    
                    if not data.empty:
                        return data
            except Exception as e:
                print(f"⚠️ FinanceDataReader 조회 실패: {e}")
                
            print(f"❌ {ticker}: 날짜별 데이터 조회 실패 ({start_date} ~ {end_date})")
            return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ {ticker} 날짜별 데이터 조회 오류: {e}")
            return pd.DataFrame()

    
    def get_market_data_by_date(self, date_str):
        """
        특정 날짜의 전체 시장 데이터 조회
        
        Args:
            date_str (str): 날짜 (YYYY-MM-DD 또는 YYYYMMDD)
            
        Returns:
            DataFrame: 해당 날짜의 전체 시장 데이터
        """
        try:
            # 날짜 형식 통일
            if '-' in str(date_str):
                pykrx_date = date_str.replace('-', '')
            else:
                pykrx_date = date_str
                
            # KOSPI + KOSDAQ 데이터 조회
            kospi_data = pystock.get_market_ohlcv(pykrx_date, market='KOSPI')
            kosdaq_data = pystock.get_market_ohlcv(pykrx_date, market='KOSDAQ')
            
            # 데이터 병합
            all_data = pd.concat([kospi_data, kosdaq_data])
            
            if all_data.empty or all_data['거래대금'].sum() == 0:
                print(f"⚠️ {date_str}: 휴장일이거나 데이터 없음")
                return pd.DataFrame()
            
            # 표준화
            all_data = self._standardize_pykrx_data(all_data)
            all_data['timestamp'] = pd.to_datetime(date_str)
            all_data.index.name = 'ticker'
            all_data = all_data.reset_index()
            
            # 거래가 없었던 종목 처리
            all_data['open'] = all_data['open'].where(all_data['open'] > 0, all_data['close'])
            all_data['high'] = all_data['high'].where(all_data['high'] > 0, all_data['close'])
            all_data['low'] = all_data['low'].where(all_data['low'] > 0, all_data['close'])
            
            return all_data
            
        except Exception as e:
            print(f"❌ {date_str} 시장 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def _standardize_pykrx_data(self, data):
        """
        pykrx 데이터 표준화
        
        Args:
            data (DataFrame): pykrx 원본 데이터
            
        Returns:
            DataFrame: 표준화된 데이터
        """
        column_mapping = {
            '시가': 'open',
            '고가': 'high',
            '저가': 'low',
            '종가': 'close',
            '거래량': 'volume',
            '거래대금': 'trade_amount',
            '등락률': 'change_rate',
            '시가총액': 'market_cap'
        }
        
        data = data.rename(columns=column_mapping)
        data.index.name = 'timestamp'
        data = data.reset_index()
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        return data
