# Data 디렉토리

이 디렉토리는 JSON 파일 형태로 데이터를 관리합니다.

## 구조 예시
```
data/
├── stock_prices/       # 주가 데이터
├── indicators/         # 계산된 지표 데이터
├── signals/           # 매매 신호 데이터
└── positions/         # 포지션 정보
```

## 파일 형식
- 모든 데이터는 JSON 형식으로 저장
- 파일명 규칙: `{종목코드}_{날짜}.json`
