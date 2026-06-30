# 토스증권 Open API 가이드

이 문서는 토스증권 Open API를 프로젝트에서 빠르게 참조하기 위한 로컬 가이드입니다.

원본 OpenAPI 스펙은 `docs/reference/tossinvest-openapi.json`에 저장했습니다.

## 기본 정보

- API 이름: 토스증권 Open API
- OpenAPI 버전: 3.1.0
- 문서 버전: 1.0.3
- Base URL: `https://openapi.tossinvest.com`
- 인증 방식: OAuth 2.0 Client Credentials Grant

## 인증

액세스 토큰은 다음 엔드포인트에서 발급합니다.

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/oauth2/token` | OAuth2 액세스 토큰 발급 |

발급받은 토큰은 이후 API 요청에 다음 헤더로 전달합니다.

```http
Authorization: Bearer {access_token}
```

계좌, 자산, 주문 관련 API는 계좌 식별자도 함께 전달해야 합니다.

```http
X-Tossinvest-Account: {accountSeq}
```

`accountSeq`는 `/api/v1/accounts` 응답에서 확인합니다.

## 엔드포인트 목록

### Account

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/accounts` | 계좌 목록 조회 |

### Asset

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/holdings` | 보유 주식 조회 |

### Market Data

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/candles` | 캔들 차트 조회 |
| GET | `/api/v1/orderbook` | 호가 조회 |
| GET | `/api/v1/price-limits` | 상/하한가 조회 |
| GET | `/api/v1/prices` | 현재가 조회 |
| GET | `/api/v1/trades` | 최근 체결 내역 조회 |

### Stock Info

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/stocks` | 종목 기본 정보 조회 |
| GET | `/api/v1/stocks/{symbol}/warnings` | 매수 유의사항 조회 |

### Market Info

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/exchange-rate` | 환율 조회 |
| GET | `/api/v1/market-calendar/KR` | 국내 장 운영 정보 조회 |
| GET | `/api/v1/market-calendar/US` | 해외 장 운영 정보 조회 |

### Order

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/api/v1/orders` | 주문 생성 |
| POST | `/api/v1/orders/{orderId}/cancel` | 주문 취소 |
| POST | `/api/v1/orders/{orderId}/modify` | 주문 정정 |

### Order History

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/orders` | 주문 목록 조회 |
| GET | `/api/v1/orders/{orderId}` | 주문 상세 조회 |

### Order Info

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/buying-power` | 매수 가능 금액 조회 |
| GET | `/api/v1/commissions` | 매매 수수료 조회 |
| GET | `/api/v1/sellable-quantity` | 판매 가능 수량 조회 |

## 구현 시 우선 순서

1. `/oauth2/token`으로 액세스 토큰 발급
2. `/api/v1/accounts`로 계좌 목록과 `accountSeq` 확인
3. 시세 조회 API로 인증/파라미터 동작 확인
4. 계좌/자산 조회 API에서 `X-Tossinvest-Account` 헤더 확인
5. 주문 API는 별도 안전장치를 둔 뒤 구현

## 주의

- 주문 생성, 정정, 취소 API는 실제 거래로 이어질 수 있으므로 테스트 코드에서 기본 비활성화 상태로 두는 것이 좋습니다.
- Rate limit과 에러 응답의 세부 필드는 `docs/reference/tossinvest-openapi.json`을 기준으로 확인합니다.
- 엔드포인트별 요청 파라미터와 응답 스키마는 원본 OpenAPI JSON을 source of truth로 사용합니다.
