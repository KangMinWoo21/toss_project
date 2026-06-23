# Goal Mode Minimal Prompt

Use this short prompt for future Codex/GPT goal-mode resumes to reduce token
usage. Keep detailed history in `docs/GOAL_MODE_CHECKPOINT.md` and archives.

```text
C:\Users\KangMinWoo\Documents\토스증권 에서 이어서 작업해줘.

목표:
실거래 실행 없이 안전한 paper-operation 자동매매 연구/운영 시스템의 완성도를 높인다.

필수 첫 행동:
1. docs/GOAL_MODE_CHECKPOINT.md 읽기
2. git status --short 확인
3. 최신 production-check / health-check 리포트 확인
4. 남은 BLOCK 원인과 이전 거절 후보를 재확인

절대 제약:
- 실제 주문 실행 기능을 추가하지 않는다.
- live trading을 기본값으로 켜지 않는다.
- Toss API를 테스트에서 호출하지 않는다.
- .env 비밀값을 출력/요약/커밋하지 않는다.
- production/readiness BLOCK은 hard stop으로 취급한다.

검증:
- python -m unittest discover -s tests
- python -m compileall -q backtester
- python -m backtester production-check --allow-blocked-exit-zero
- python -m backtester health-check --scalper-mode warn --allow-blocked-exit-zero

작업 방식:
- broad sweep 대신 현재 checkpoint의 남은 blocker에서 시작한다.
- 코드 변경은 테스트 먼저 추가한다.
- 중요한 루프가 끝나면 checkpoint를 짧게 갱신하고 커밋/푸시한다.
```
