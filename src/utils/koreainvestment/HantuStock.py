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
                
    def get_header(self, tr_id, add_prefix=True):
        """
        API 요청 헤더 생성
        
        Args:
            tr_id (str): TR ID 또는 TR ID suffix
            add_prefix (bool): 모드에 따라 T/V prefix 추가 여부
                - True: 모드별 prefix 추가 (주문/계좌 API용, 예: TTC0802U → TTTC0802U)
                - False: TR ID 그대로 사용 (시세 조회 API용, 예: FHKST01010100)
            
        Returns:
            dict: 요청 헤더
        """
        # prefix 추가 여부에 따라 TR ID 결정
        if add_prefix:
            final_tr_id = f"{self._tr_prefix}{tr_id}"
        else:
            final_tr_id = tr_id
        
        headers = {
            "content-type": "application/json",
            "appkey": self._api_key, 
            "appsecret": self._secret_key,
            "authorization": f"Bearer {self._access_token}",
            "tr_id": final_tr_id,
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
    
    def inquire_price(self, ticker):
        """
        특정 종목의 현재가 조회
        
        Args:
            ticker (str): 종목 코드
            
        Returns:
            float: 현재가
        """
        try:
            headers = self.get_header('FHKST01010100', add_prefix=False)  # 국내주식 기본시세 조회
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": ticker
            }
            
            url = self._base_url + '/uapi/domestic-stock/v1/quotations/inquire-price'
            hd, res = self._requests(url, headers, params)
            
            if res['rt_cd'] == '0':
                current_price = float(res['output']['stck_prpr'])
                return current_price
            else:
                print(f"현재가 조회 실패: {res['msg1']}")
                return None
                
        except Exception as e:
            print(f"현재가 조회 중 오류 발생: {e}")
            return None
    
    def inquire_daily_price(self, ticker, start_date=None, end_date=None, adj_price=True):
        """
        특정 종목의 일봉 데이터 조회
        
        Args:
            ticker (str): 종목 코드
            start_date (str, optional): 시작일 (YYYYMMDD). None이면 최근 100일
            end_date (str, optional): 종료일 (YYYYMMDD). None이면 오늘
            adj_price (bool): 수정주가 여부
            
        Returns:
            DataFrame: 일봉 데이터
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            if start_date is None:
                # 최근 100일 (주말 포함하여 150일 전부터)
                start_date = (datetime.now() - timedelta(days=150)).strftime('%Y%m%d')
            
            headers = self.get_header('FHKST03010100', add_prefix=False)  # 국내주식 기간별 시세 조회
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": ticker,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_period_div_code": "D",  # D: 일봉
                "fid_org_adj_prc": "0" if adj_price else "1"  # 0: 수정주가, 1: 원주가
            }
            
            url = self._base_url + '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
            hd, res = self._requests(url, headers, params)
            
            if res['rt_cd'] == '0' and res['output2']:
                df = pd.DataFrame(res['output2'])
                print(f'df.columns: {df.columns}')
                # 날짜를 인덱스로 설정
                df['stck_bsop_date'] = pd.to_datetime(df['stck_bsop_date'])
                df = df.set_index('stck_bsop_date')
                df.index.name = 'Date'
                
                # 데이터 타입 변환
                numeric_columns = ['stck_oprc', 'stck_hgpr', 'stck_lwpr', 'stck_clpr', 'acml_vol']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 날짜 역순 정렬 (과거 -> 최근)
                df = df.sort_index()
                
                return df
            else:
                print(f"일봉 데이터 조회 실패: {res['msg1']}")
                return None
                
        except Exception as e:
            print(f"일봉 데이터 조회 중 오류 발생: {e}")
            return None
    
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
