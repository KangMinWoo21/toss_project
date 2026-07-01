# 미국주식 Paper-Only Factor Risk Model

## 목적

`auto-paper-factor-risk`는 미국주식 paper-only 목표비중을 기관식 리스크 관점으로 점검하는 로컬 CSV 전용 검사다. 실시간 브로커, KIS, Toss, yfinance 호출은 하지 않으며, 주문 실행 가능 상태도 만들지 않는다.

## 입력

- 목표비중 CSV: 기본 `data/auto_trading/kis_us_targets_from_auto_paper_risk_adjusted.csv`
- 무료 외부 데이터 디렉터리: 기본 `data/auto_trading/free_external_data`
- 필수 factor CSV: `factors.csv`

`factors.csv`는 최소한 다음 컬럼을 가진다.

- `symbol`
- `sector`
- `beta`
- `size_score`
- `value_score`
- `quality_score`
- `momentum_score`
- `source`
- `as_of`

## 검사 항목

- `single_name_exposure`: 단일 종목 목표비중 한도
- `sector_exposure`: 섹터별 목표비중 한도
- `weighted_beta`: 현금 beta를 0으로 둔 포트폴리오 beta proxy
- `weighted_size_score`: 보고 전용
- `weighted_value_score`: 보고 전용
- `weighted_quality_score`: 보고 전용
- `quality_tilt`: 낮은 quality tilt 한도
- `weighted_momentum_score`: 보고 전용

기본 한도는 다음과 같다.

- `max_single_weight=0.35`
- `max_sector_weight=0.50`
- `max_weighted_beta=1.50`
- `max_negative_quality_tilt=0.20`

## 안전 정책

입력 목표비중의 모든 행은 다음 값을 가져야 한다.

- `paper_only=True`
- `dry_run=True`
- `execution_allowed=False`
- `production_effect=none`

출력 CSV와 Markdown도 동일한 안전 플래그를 보존한다. 하나라도 한도를 넘으면 CLI는 리포트를 저장하되 exit code `2`를 반환한다.

## 실행

```powershell
python -m backtester auto-paper-factor-risk
```

기본 산출물:

- `data/reports/auto_trading/auto_paper_factor_risk.csv`
- `data/reports/auto_trading/auto_paper_factor_risk.md`

## 한계

v1은 무료 데이터 기반 factor proxy다. Barra/Axioma 수준의 공분산 모델, 산업 중립 최적화, 실시간 exposure drift는 포함하지 않는다. 이 단계는 paper-only 엔진의 사전 리스크 게이트이며, 실주문 승인 신호가 아니다.
