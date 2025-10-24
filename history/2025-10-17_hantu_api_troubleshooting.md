# HantuStock API 문제 해결

## 날짜
2025-10-17

## 작업 내용

### 1. 문제 발견
- **현상**: `get_current_price()`, `get_past_data_by_date()` 테스트 실패
- **에러 메시지**: 
  ```
  ERROR at _requests: {'rt_cd': '1', 'msg_cd': 'OPSQ0002', 'msg1': '없는 서비스 코드 입니다.'}
  ```

### 2. 문제 분석
- **원인 1**: 모의투자 환경에서 일부 한국투자증권 API 제한
  - 실시간 현재가 조회 API 미지원
  - 일부 TR ID가 모의투자에서 작동하지 않음
  
- **원인 2**: TR ID 오류
  - `FHKST01010100` (현재가 조회) → 모의투자에서 지원 안 됨
  - `FHKST01010400` (일봉 조회) → 파라미터 형식 다를 가능성

### 3. 해결 방안
- **대안 1**: 기존 작동하는 메서드 활용
- **대안 2**: 외부 라이브러리 직접 사용 (pykrx, FinanceDataReader)
- **대안 3**: 폴백 메커니즘 구현

### 4. 구현 내용

#### get_current_price() 수정
```python
# 변경 전: 한국투자증권 API 직접 호출
# 변경 후: 다중 소스 폴백 방식
1. 기존 get_past_data(n=1) 활용 - 가장 안정적
2. pykrx로 당일 데이터 조회
```

#### get_past_data_by_date() 수정
```python
# 변경 전: 한국투자증권 API 우선
# 변경 후: pykrx 우선 사용
1. pykrx (KOSPI/KOSDAQ) - 모의투자에서도 안정적
2. FinanceDataReader - 전체 데이터 조회 후 필터링
```

### 5. 장단점 분석

#### 장점
- 모의투자 환경에서 안정적 작동
- 다중 소스로 데이터 가용성 향상
- 기존 테스트 통과

#### 단점
- 실시간성 제한 (장 마감 후 데이터)
- 외부 라이브러리 의존성 증가
- 일부 기능 제한 (분봉, 틱 데이터 등)

## 이슈

### 이슈 1: API 문서와 실제 동작 불일치
- **문제**: 한국투자증권 API 문서의 TR ID가 모의투자에서 작동 안 함
- **해결**: 실제 작동하는 방식으로 대체

### 이슈 2: 실시간 데이터 제약
- **문제**: pykrx, FDR은 장 마감 후 데이터만 제공
- **영향**: 장 중 실시간 전략 실행 제한
- **대안**: 실거래 모드에서는 한투 API 재시도 가능

### 이슈 3: 테스트 코드 논리 오류
- **문제**: `result['high'].min() >= result['low'].max()` 검증 로직 오류
- **원인**: 전체 기간의 최소 고가와 최대 저가를 비교하는 잘못된 로직
- **해결**: 각 날짜별로 `high >= low` 검증으로 수정
  ```python
  assert (result['high'] >= result['low']).all()
  assert (result['close'] <= result['high']).all()
  assert (result['close'] >= result['low']).all()
  ```

## 참고 사항

### 향후 개선 방향
1. 실거래 모드에서는 한국투자증권 API 우선 사용
2. 웹소켓 기반 실시간 데이터 구독 검토
3. 캐싱 레이어 추가로 성능 개선

### 테스트 방법
```bash
# 확장 API 테스트
pytest src/tests/test_hantu_api_extended.py -v

# 데이터 수집 모듈 테스트
pytest src/tests/test_data_collector.py -v
```

## 다음 단계
1. 수정된 API로 DataCollector 모듈 테스트 확인
2. 기술적 지표 계산 모듈 개발 진행