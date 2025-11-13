# 데이터 수집 모듈 구현

## 날짜
2025-10-30

## 작업 내용

### 1. collector.py 모듈 구현
`src/data/collector.py` - 주가 데이터 수집 및 정규화 모듈

#### 구현된 함수 목록

**핵심 함수 (3개)**
1. **`get_stock_data()`** - 통합 데이터 수집 인터페이스
   - 자동 소스 선택 (최근 100일 이내: API, 이상: FDR)
   - strategy와 backtest 모두에서 사용할 메인 함수
   - 파라미터: ticker, start_date, end_date, period, source

2. **`get_real_time_data()`** - 실시간/최근 데이터 조회
   - HantuStock API 사용
   - 실시간 전략 실행 시 사용
   - 파라미터: ticker, period, count

3. **`get_historical_data()`** - 과거 데이터 조회
   - FinanceDataReader 또는 pykrx 사용
   - 백테스팅용 장기간 데이터
   - 파라미터: ticker, start_date, end_date, source

**보조 함수 (5개)**
4. **`get_multiple_stocks()`** - 다종목 병렬 수집
   - ThreadPoolExecutor로 최대 5개 병렬 처리
   - 포트폴리오 백테스팅용

5. **`get_current_price()`** - 현재가 조회
   - HantuStock API 사용
   - 빠른 가격 확인용

6. **`get_market_status()`** - 장 상태 확인
   - 시간대별 상태 반환 (open/close/pre_market/after_hours)

7. **`validate_data()`** - 데이터 검증
   - 필수 컬럼 확인
   - 이상치 탐지 (음수, 0값, High < Low)
   - 최소 행 수 검증

8. **`_normalize_dataframe()`** - 데이터 정규화 (내부 함수)
   - 다양한 소스의 DataFrame을 표준 형식으로 변환
   - 컬럼명 통일: Open, High, Low, Close, Volume
   - datetime 인덱스 변환 및 오름차순 정렬
   - 결측치 및 중복 제거

#### 표준 DataFrame 형식
```python
                       Open    High     Low   Close    Volume
Date                                                          
2024-01-02 00:00:00  60000   61000   59500   60500  10000000
2024-01-03 00:00:00  60500   62000   60000   61500  12000000
```

**특징**:
- Index: datetime 타입 (오름차순 정렬)
- Columns: 대문자 시작 (Open, High, Low, Close, Volume)
- 데이터 타입: 가격=float, Volume=int64

---

### 2. 테스트 코드 작성
`src/tests/test_collector.py` - 성공 케이스 테스트

#### 테스트 클래스 구조
```python
TestNormalizeDataFrame        # 정규화 함수 테스트
├── test_normalize_fdr_format       # FDR 형식 변환
└── test_normalize_pykrx_format     # pykrx 형식 변환

TestValidateData              # 검증 함수 테스트
├── test_validate_valid_data        # 정상 데이터
└── test_validate_with_min_rows     # 최소 행 수

TestGetHistoricalData         # 과거 데이터 수집 테스트
├── test_get_historical_data_fdr    # FDR 소스
└── test_get_historical_data_pykrx  # pykrx 소스

TestGetRealTimeData           # 실시간 데이터 수집 테스트
└── test_get_real_time_data_daily   # 일봉 데이터

TestGetStockData              # 통합 인터페이스 테스트
├── test_get_stock_data_auto_recent      # 자동 선택 (최근)
├── test_get_stock_data_auto_historical  # 자동 선택 (과거)
└── test_get_stock_data_default_params   # 기본 파라미터

TestGetMultipleStocks         # 다종목 수집 테스트
└── test_get_multiple_stocks_success     # 병렬 수집

TestGetCurrentPrice           # 현재가 조회 테스트
└── test_get_current_price_success

TestGetMarketStatus           # 장 상태 확인 테스트
└── test_get_market_status_success
```

**테스트 실행 방법**:
```bash
# 전체 테스트
pytest src/tests/test_collector.py -v

# 특정 클래스만
pytest src/tests/test_collector.py::TestGetStockData -v
```

---

### 3. 문서화
`src/data/README.md` - 사용 가이드 및 API 문서

**포함 내용**:
- 모듈 개요 및 주요 기능
- 전체 함수 목록 및 사용 예시
- 반환 데이터 형식 설명
- 실전 사용 예시 (strategy, backtest)
- 테스트 실행 방법
- 주의사항 및 에러 처리
- 다음 단계 안내

---

## 주요 특징

### 1. 데이터 소스 자동 선택
```python
# 최근 100일 이내 → API 사용
df = get_stock_data('005930', source='auto')

# 100일 초과 → FDR 사용
df = get_stock_data('005930', '2020-01-01', '2023-12-31', source='auto')
```

### 2. 통일된 인터페이스
- strategy와 backtest에서 동일한 함수 사용
- 소스만 바꿔도 같은 형식의 데이터 반환

### 3. 병렬 처리
```python
# 여러 종목 동시 수집 (최대 5개 병렬)
data = get_multiple_stocks(['005930', '000660', '035420'])
```

### 4. 자동 검증
- 데이터 수집 시 자동으로 validate_data() 호출
- 이상치 자동 탐지 및 제거

---

## 파일 구조

```
src/
├── data/
│   ├── __init__.py           # 모듈 export
│   ├── collector.py          # ✅ 데이터 수집 모듈
│   └── README.md             # ✅ 사용 가이드
│
└── tests/
    └── test_collector.py     # ✅ 테스트 코드
```

---

## 기술적 세부사항

### 1. 의존성
- **pandas**: DataFrame 처리
- **numpy**: 수치 계산
- **FinanceDataReader**: 과거 데이터 수집
- **pykrx**: 한국거래소 데이터
- **HantuStock**: 실시간 API (기존 구현 활용)

### 2. 에러 처리
- try-except로 각 함수 보호
- 명확한 에러 메시지 제공
- logging으로 디버깅 정보 기록

### 3. 성능 최적화
- 병렬 처리 (ThreadPoolExecutor)
- 벡터화 연산 (pandas)
- 불필요한 복사 최소화

### 4. 코드 품질
- 타입 힌팅 (Type Hints)
- Google 스타일 docstring
- 명확한 함수명 및 변수명

---

## 테스트 결과

```bash
$ pytest src/tests/test_collector.py -v

test_collector.py::TestNormalizeDataFrame::test_normalize_fdr_format ✅
test_collector.py::TestNormalizeDataFrame::test_normalize_pykrx_format ✅
test_collector.py::TestValidateData::test_validate_valid_data ✅
test_collector.py::TestValidateData::test_validate_with_min_rows ✅
test_collector.py::TestGetHistoricalData::test_get_historical_data_fdr ✅
test_collector.py::TestGetHistoricalData::test_get_historical_data_pykrx ✅
test_collector.py::TestGetRealTimeData::test_get_real_time_data_daily ✅
test_collector.py::TestGetStockData::test_get_stock_data_auto_recent ✅
test_collector.py::TestGetStockData::test_get_stock_data_auto_historical ✅
test_collector.py::TestGetStockData::test_get_stock_data_default_params ✅
test_collector.py::TestGetMultipleStocks::test_get_multiple_stocks_success ✅
test_collector.py::TestGetCurrentPrice::test_get_current_price_success ✅
test_collector.py::TestGetMarketStatus::test_get_market_status_success ✅

✅ 13 passed (성공 케이스만 테스트)
```

---

## 다음 단계

### Level 2: 기술적 지표 계산 모듈
`src/analysis/technical/indicators.py`

**구현 예정**:
1. **EMA 계산**: 5일, 20일, 40일
2. **MACD 3종 조합**:
   - MACD(상): 5|20|9
   - MACD(중): 5|40|9
   - MACD(하): 20|40|9
3. **ATR 계산**: 포지션 사이징용
4. **히스토그램 & 시그널선**: MACD 구성 요소
5. **피크아웃 감지**: 방향 전환 감지

**일정**: 1-2일 예상

---

## 이슈 및 해결

### 이슈 1: HantuStock API 경로 문제
- **문제**: src/data에서 src/utils/koreainvestment 접근 불가
- **해결**: sys.path에 상대 경로 추가
```python
utils_path = os.path.join(os.path.dirname(__file__), '..', 'utils')
sys.path.insert(0, utils_path)
```

### 이슈 2: pykrx 날짜 형식
- **문제**: pykrx는 YYYYMMDD 형식 요구
- **해결**: start_date.replace('-', '')로 변환

### 이슈 3: 컬럼명 불일치
- **문제**: 각 소스마다 다른 컬럼명 사용
- **해결**: _normalize_dataframe()로 표준화

---

## 참고 자료

- [개발 계획](plan/2025-10-30_common_modules_planning.md)
- [API 연동 가이드](./2025-10-15_api_integration_and_testing.md)
- [프로젝트 README](../README.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-10-30: 데이터 수집 모듈 구현 완료 ✅
