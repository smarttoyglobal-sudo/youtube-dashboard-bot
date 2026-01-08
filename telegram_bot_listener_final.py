#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텔레그램 봇 리스너 FINAL - 24/7 실행
"""

import requests
import subprocess
import time
import os
import sys

# 한글 인코딩 문제 해결
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# ==================== 설정 ====================
# 환경 변수에서 가져오기 (Render.com용) 또는 직접 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8589679004:AAG8vsa2kh4MdDqWXjheCWGn6PbR1b0Y1SI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6046105835")
# ==============================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_SCRIPT = os.path.join(SCRIPT_DIR, "youtube_dashboard_final_v4.py")

def send_message(text):
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def get_updates(offset=None):
    """텔레그램 업데이트 가져오기"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except:
        return None

def run_dashboard():
    """대시보드 실행"""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["python", DASHBOARD_SCRIPT, "--telegram"],
                cwd=SCRIPT_DIR,
                timeout=300
            )
        else:
            subprocess.run(
                ["python3", DASHBOARD_SCRIPT, "--telegram"],
                cwd=SCRIPT_DIR,
                timeout=300
            )
        return True
    except Exception as e:
        print(f"대시보드 실행 오류: {e}")
        return False

def main():
    print("=" * 50)
    print("🤖 텔레그램 봇 리스너 FINAL 시작")
    print("=" * 50)
    print("\n사용법:")
    print("  - '업데이트' 또는 아무 메시지: 대시보드 즉시 업데이트")
    print("  - /start: 도움말")
    print("\n대기 중...\n")
    
    send_message("🤖 봇이 시작되었습니다!\n\n'업데이트'를 보내면 즉시 대시보드를 업데이트합니다.")
    
    last_update_id = None
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update["update_id"] + 1
                    
                    if "message" in update:
                        message = update["message"]
                        text = message.get("text", "")
                        
                        print(f"[{time.strftime('%H:%M:%S')}] 메시지 수신: {text}")
                        
                        if text == "/start":
                            help_text = """
🤖 YouTube 대시보드 봇 FINAL

📊 기능:
- 매 시간 자동 업데이트
- 60분 변화량
- 48시간 롤링 변화량
- 급등 채널 알림

💬 명령어:
- '업데이트': 즉시 대시보드 업데이트
- 아무 메시지: 업데이트 실행
"""
                            send_message(help_text)
                        else:
                            # 모든 메시지에 대해 업데이트 실행
                            send_message("⏳ 업데이트 중... 잠시만 기다려주세요!")
                            
                            success = run_dashboard()
                            
                            if not success:
                                send_message("❌ 업데이트 실패!")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n봇 종료")
            send_message("🤖 봇이 종료되었습니다.")
            break
        except Exception as e:
            print(f"오류: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
