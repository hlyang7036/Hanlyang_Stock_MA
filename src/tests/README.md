# 테스트 가이드

한국투자증권 API 및 전략 로직 테스트를 위한 가이드입니다.

## 📦 필요한 패키지 설치

```bash
# pytest 및 관련 패키지 설치
uv pip install pytest pytest-cov pytest-mock

# 또는 전체 패키지 설치
uv pip install pandas requests finance-datareader pykrx python-dateutil pyyaml pytest pytest-cov pytest-mock
```

## 🧪 테스트 실행 방법

### 전체 테스트 실행

```bash
# 프로젝트 루트에서 실행
pytest src/tests/test_hantu_api.py -v

# 또는 상세 출력 포함
pytest src/tests/test_hantu_api.py -v -s
```

### 특정 테스트 클래스만 실행

```bash
# API 연결 테스트만
pytest src/tests/test_hantu_api.py::TestHantuAPIConnection -v

# 시장 데이터 조회 테스트만
pytest src/tests/test_hantu_api.py::TestHantuAPIMarketData -v

# 계좌 정보 테스트만
pytest src/tests/test_hantu_api.py::TestHantuAPIAccount -v
```

### 특정 테스트 함수만 실행

```bash
pytest src/tests/test_hantu_api.py::TestHantuAPIConnection::test_get_access_token -v
```

### 마커를 사용한 선택적 실행

```bash
# 느린 테스트 제외
pytest src/tests/test_hantu_api.py -m "not slow" -v

# 건너뛴 테스트 포함
pytest src/tests/test_hantu_api.py --runxfail -v
```

### 커버리지 측정

```bash
pytest src/tests/test_hantu_api.py --cov=src/utils/koreainvestment --cov-report=html
```

## 📋 테스트 구조

### 테스트 클래스

| 클래스 | 설명 | 주요 테스트 |
|--------|------|-------------|
| `TestHantuAPIConnection` | API 연결 및 인증 | 토큰 발급, 헤더 생성 |
| `TestHantuAPIMarketData` | 시장 데이터 조회 | 과거 데이터, 전체 시장 데이터 |
| `TestHantuAPIAccount` | 계좌 정보 조회 | 보유 현금, 보유 주식 |
| `TestHantuAPIOrder` | 주문 기능 | 매수/매도 주문 (⚠️ 실제 주문 발생) |
| `TestHantuAPIIntegration` | 통합 테스트 | 전체 워크플로우 |

### Fixtures (conftest.py)

- `api_credentials`: API 인증 정보
- `hantu_api`: HantuStock API 인스턴스 (세션 스코프)
- `test_ticker`: 테스트용 종목 코드 (삼성전자: 005930)

## ⚠️ 주의사항

### 1. 환경 설정
- `.env` 파일이 올바르게 설정되어 있어야 합니다.
- 모의투자 모드로 테스트하는 것을 권장합니다.

### 2. 네트워크 연결
- 실제 API를 호출하므로 인터넷 연결이 필요합니다.
- API 호출 제한(초당 거래건수)에 주의하세요.

### 3. 주문 테스트
- `TestHantuAPIOrder` 클래스는 실제 주문이 발생합니다!
- 기본적으로 `@pytest.mark.skip`으로 비활성화되어 있습니다.
- 테스트하려면 해당 데코레이터를 제거하고 신중하게 실행하세요.

### 4. 느린 테스트
- `@pytest.mark.slow`가 붙은 테스트는 시간이 오래 걸립니다.
- `pytest -m "not slow"`로 빠른 테스트만 실행할 수 있습니다.

## 📊 예상 출력 예시

```
========================================== test session starts ===========================================
collected 12 items

src/tests/test_hantu_api.py::TestHantuAPIConnection::test_api_initialization PASSED           [  8%]
✅ API 초기화 성공
   Access Token: eyJ0eXAiOiJKV1QiLCJh...

src/tests/test_hantu_api.py::TestHantuAPIConnection::test_get_access_token PASSED             [ 16%]
✅ 접근 토큰 발급 성공
   Token: eyJ0eXAiOiJKV1QiLCJh...

src/tests/test_hantu_api.py::TestHantuAPIMarketData::test_get_past_data_single PASSED        [ 25%]
✅ 단일 데이터 조회 성공
   종목: 005930
   종가: 71,800원

...

============================================ 12 passed in 5.23s ==============================================
```

## 🔧 트러블슈팅

### 토큰 발급 실패
```
ERROR: get_access_token error
```
→ `.env` 파일의 API Key와 Secret Key를 확인하세요.

### 데이터 조회 실패
```
ERROR at _requests: {'rt_cd': '1', ...}
```
→ API 호출 제한을 초과했을 수 있습니다. 잠시 후 다시 시도하세요.

### Import 에러
```
ModuleNotFoundError: No module named 'pytest'
```
→ `uv pip install pytest`로 pytest를 설치하세요.

## 📝 테스트 추가하기

새로운 기능을 추가할 때는 해당하는 테스트도 함께 작성하세요:

```python
class TestNewFeature:
    """새로운 기능 테스트"""
    
    def test_new_function(self, hantu_api):
        """새로운 함수 테스트"""
        result = hantu_api.new_function()
        assert result is not None
        print(f"\n✅ 새로운 기능 테스트 성공")
```

## 📚 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [한국투자증권 Open API 문서](https://apiportal.koreainvestment.com/)
