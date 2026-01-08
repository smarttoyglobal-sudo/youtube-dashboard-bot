# YouTube Multi-Channel Dashboard v4

전체 쇼츠 영상 추적 + 이미지 차트 생성

## 기능
- 채널별 전체 쇼츠 조회수 합계 추적
- 60분 / 48시간 정확한 변화량 계산
- 이미지 차트 생성 (matplotlib)
- 급등 영상 자동 감지 (50%+)
- 텔레그램 자동 전송

## 파일 구조
- `youtube_dashboard_final_v4.py` - 메인 데이터 수집 스크립트
- `telegram_bot_listener_final.py` - 텔레그램 봇 리스너
- `requirements.txt` - Python 패키지
- `render.yaml` - Render.com 배포 설정

## 로컬 실행
```bash
pip install -r requirements.txt
python youtube_dashboard_final_v4.py --telegram
```

## Render.com 배포
1. GitHub에 푸시
2. Render.com 계정 연결
3. New Web Service + Cron Job 생성
4. 환경 변수 설정
5. Deploy!

## 환경 변수
- `YOUTUBE_API_KEY` - YouTube Data API v3 키
- `TELEGRAM_BOT_TOKEN` - Telegram Bot Token
- `TELEGRAM_CHAT_ID` - Telegram Chat ID
