# 프로젝트 초기 설정

## 날짜
2025-10-14

## 작업 내용
- Git 저장소 초기화
- README.md 작성
- .gitignore 설정 (uv 가상환경 제외)
- 프로젝트 디렉토리 구조 생성
  - `src/` - 소스 코드
  - `data/` - JSON 데이터 관리
  - `history/` - 개발 이력
  - `log/` - 실행 로그

## 이슈
### GitHub Push 인증 오류
- **문제**: HTTPS 방식으로 push 시 인증 실패
- **원인**: GitHub에서 비밀번호 인증 미지원
- **해결**: Personal Access Token 또는 SSH 키 사용 필요

## 참고 사항
- 가상환경 도구: uv 사용
- 데이터 저장 방식: JSON 파일 (DB 미사용)
- 전략 문서: `Moving_Average_Investment_Strategy_Summary.md` 참조
