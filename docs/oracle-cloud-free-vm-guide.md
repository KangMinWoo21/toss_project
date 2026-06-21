# Oracle Cloud Always Free VM 운영 가이드

이 가이드는 노트북이 꺼져 있어도 Toss Open API 기반 데이터 수집기를 계속 돌리기 위한 최소 운영 방식이다. 서버는 수집과 임시 저장만 맡고, 분석과 백테스트는 나중에 노트북에서 실행한다.

## 목표 구조

```text
Oracle Cloud Always Free VM
-> Toss Open API 호출
-> data/scalper/*.csv 저장
-> backups/*.zip 백업
-> 노트북에서 scp로 다운로드
```

## 1. 무료 VM 만들기

Oracle Cloud에서 Compute Instance를 만들 때 다음을 확인한다.

- Shape에 Always Free eligible 표시가 있어야 한다.
- OS는 Ubuntu 22.04 또는 24.04를 권장한다.
- SSH private key는 노트북에 안전하게 저장한다.
- 방화벽은 SSH 22번만 열어도 된다. 이 수집기는 외부에서 HTTP 요청을 받을 필요가 없다.

무료 리소스라도 설정을 잘못 잡으면 과금될 수 있으니 예산 알림을 먼저 켜는 것이 좋다.

## 2. 서버 준비

서버에 SSH로 접속한 뒤 기본 도구를 설치한다.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv zip
```

프로젝트를 서버에 올린다. GitHub에 올려둘 경우:

```bash
git clone <your-repo-url> ~/toss-stock-bot
cd ~/toss-stock-bot
```

GitHub를 쓰지 않을 경우 노트북에서 압축 파일을 올려도 된다.

```powershell
scp -i "C:\path\to\oracle.key" "C:\Users\KangMinWoo\Documents\토스증권\project.zip" ubuntu@서버IP:/home/ubuntu/
```

## 3. .env 만들기

서버의 프로젝트 폴더에서 `.env`를 만든다. API 키는 코드나 GitHub에 넣지 않는다.

```bash
cd ~/toss-stock-bot
nano .env
```

내용:

```env
TOSSINVEST_CLIENT_ID=your_client_id
TOSSINVEST_CLIENT_SECRET=your_client_secret
```

권한을 제한한다.

```bash
chmod 600 .env
```

## 4. 수동 실행 테스트

처음에는 10초 정도만 실행해서 CSV가 생기는지 확인한다.

```bash
cd ~/toss-stock-bot
chmod +x scripts/cloud/*.sh
SYMBOL=005930 ITERATIONS=10 INTERVAL_SECONDS=1 ./scripts/cloud/run_scalper.sh
ls -lh data/scalper
```

미국주식 심볼이 Toss API에서 지원되면 `SYMBOL=AAPL` 같은 방식으로 바꿔 테스트한다. 심볼 형식은 Toss API 응답을 보고 맞춰야 한다.

## 5. 자동 실행 등록

서비스 파일을 복사한다.

```bash
sudo cp ~/toss-stock-bot/scripts/cloud/toss-scalper.service /etc/systemd/system/toss-scalper.service
sudo systemctl daemon-reload
sudo systemctl enable toss-scalper
sudo systemctl start toss-scalper
```

상태 확인:

```bash
systemctl status toss-scalper --no-pager
journalctl -u toss-scalper -f
```

종목을 바꾸려면 서비스 파일의 `Environment=SYMBOL=005930` 값을 수정한 뒤 재시작한다.

```bash
sudo systemctl daemon-reload
sudo systemctl restart toss-scalper
```

## 6. 백업 만들기

하루치 CSV를 zip으로 묶는다.

```bash
cd ~/toss-stock-bot
./scripts/cloud/backup_scalper.sh
```

매일 장 이후 자동 백업하려면 cron에 등록한다.

```bash
crontab -e
```

예시:

```cron
10 16 * * 1-5 cd /home/ubuntu/toss-stock-bot && /usr/bin/bash scripts/cloud/backup_scalper.sh >> backups/backup.log 2>&1
```

서버 시간이 UTC일 수 있으니 `date`와 `timedatectl`로 시간대를 확인한다.

## 7. 노트북으로 데이터 내려받기

PowerShell에서 실행한다.

```powershell
cd "C:\Users\KangMinWoo\Documents\토스증권"
.\scripts\download_scalper_data.ps1 -Server "ubuntu@서버IP" -IdentityFile "C:\path\to\oracle.key"
```

기본 저장 위치:

```text
C:\Users\KangMinWoo\Documents\토스증권\data\scalper_cloud
```

## 8. 운영 원칙

- 실제 주문은 붙이지 않고 paper-scalp 데이터부터 충분히 쌓는다.
- `.env`와 SSH key는 GitHub에 올리지 않는다.
- 서버 디스크가 작으면 `data/scalper`와 `backups` 용량을 주기적으로 확인한다.
- 초단기 전략 평가는 수익률보다 스프레드, 신호 빈도, 체결 가능성, 손절 빈도를 같이 봐야 한다.
