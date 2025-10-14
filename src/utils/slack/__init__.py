"""
Slack 알림 패키지

Slack을 통한 알림 기능을 제공하는 패키지입니다.

주요 기능:
- 매매 신호 알림
- 백테스팅 결과 알림
- 에러 알림
- 일일 리포트 알림
- 포지션 변경 알림

사용 예시:
    from src.utils.slack import send_message
    
    send_message(
        channel="#trading-alerts",
        message="매수 신호 발생: 삼성전자"
    )
"""
