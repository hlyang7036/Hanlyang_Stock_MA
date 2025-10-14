# Log 디렉토리

백테스팅 및 crontab 실행 결과의 로그를 저장하는 디렉토리입니다.

## 로그 파일 구조

### 백테스팅 로그
- 경로: `log/backtest/`
- 파일명: `backtest_{날짜}_{시간}.log`
- 예시: `backtest_20251014_153000.log`

### Crontab 실행 로그
- 경로: `log/cron/`
- 파일명: `cron_{작업명}_{날짜}.log`
- 예시: `cron_daily_signal_20251014.log`

### 에러 로그
- 경로: `log/error/`
- 파일명: `error_{날짜}.log`
- 예시: `error_20251014.log`

## 로그 레벨
- `DEBUG`: 상세한 디버깅 정보
- `INFO`: 일반 정보 메시지
- `WARNING`: 경고 메시지
- `ERROR`: 에러 메시지
- `CRITICAL`: 심각한 에러

## 주의사항
- 로그 파일은 `.gitignore`에 포함되어 Git에 커밋되지 않음
- 주기적으로 오래된 로그 파일 정리 필요 (30일 이상)
