#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 멀티채널 대시보드 FINAL
- 전체 쇼츠 추적 (90초 기준)
- 텔레그램 자동 전송
- Render Cron Job 최적화
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
import re
import isodate

# Matplotlib 설정
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정
if sys.platform.startswith('win'):
    plt.rc('font', family='Malgun Gothic')
else:
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        plt.rc('font', family=font_prop.get_name())

plt.rcParams['axes.unicode_minus'] = False

# 환경 변수
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', 'AIzaSyA3MfhHkG1fhPEl04ZyDKS2IkFxyQGijvA')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8589679004:AAG8vsa2kh4MdDqWXjheCWGn6PbR1b0Y1SI')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6046105835')

# 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(SCRIPT_DIR, 'channels.json')
HISTORY_FILE = os.path.join(SCRIPT_DIR, 'youtube_history.json')

def load_channels():
    """채널 목록 로드"""
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 기본 채널 목록
    return [
        {'name': '배꼽나와', 'id': 'UCoLCO6_rNMT8EwUTvt3gsgw'},
        {'name': '심장톡톡', 'id': 'UC5kAxeHTWkWk1QJeRWTtCsg'},
        {'name': '포동무비(스릴러)', 'id': 'UCHfRM7W64VcYjLQ7p2yUCvA'},
        {'name': '힐링토끼', 'id': 'UCfqiAcrz-k5dxl-M3iMzvwQ'},
        {'name': '도도tv(원영)', 'id': 'UCwlwXPNmRN_f6e4xH_hL-RA'},
        {'name': '숏숏냥이(참교육)', 'id': 'UCzqb5DK02vBcJWnoCCCBo1Q'},
        {'name': '사이다tv', 'id': 'UCKZf0VOSvoxzc4v29Aqrj7Q'},
        {'name': '오전', 'id': 'UCOp6a5dNbFGEGd_WsIdT2qg'},
        {'name': '감동하다', 'id': 'UC5OwGjpuLBfU06SjdGDNEEA'}
    ]

def load_history():
    """히스토리 로드"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_history(history):
    """히스토리 저장"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_all_shorts(channel_id, max_pages=10):
    """채널의 모든 쇼츠 수집 (90초 이하)"""
    all_videos = []
    next_page_token = None
    page_count = 0
    
    while page_count < max_pages:
        try:
            url = 'https://www.googleapis.com/youtube/v3/search'
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'maxResults': 50,
                'order': 'date',
                'type': 'video',
                'key': YOUTUBE_API_KEY
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ API 오류 {response.status_code}: {response.text[:200]}")
                break
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                break
            
            video_ids = [item['id']['videoId'] for item in items]
            
            # 비디오 상세 정보 가져오기
            details_url = 'https://www.googleapis.com/youtube/v3/videos'
            details_params = {
                'part': 'contentDetails,statistics,snippet',
                'id': ','.join(video_ids),
                'key': YOUTUBE_API_KEY
            }
            
            details_response = requests.get(details_url, params=details_params, timeout=30)
            
            if details_response.status_code == 200:
                details_data = details_response.json()
                
                for video in details_data.get('items', []):
                    duration = video['contentDetails']['duration']
                    duration_seconds = int(isodate.parse_duration(duration).total_seconds())
                    
                    # 90초 이하만 쇼츠로 인식
                    if duration_seconds <= 90:
                        all_videos.append({
                            'videoId': video['id'],
                            'title': video['snippet']['title'],
                            'duration': duration_seconds,
                            'viewCount': int(video['statistics'].get('viewCount', 0))
                        })
            
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
            
            page_count += 1
            
        except Exception as e:
            print(f"❌ 수집 오류: {e}")
            break
    
    return all_videos

def format_number(num):
    """숫자 포맷팅 (한국어)"""
    if num >= 10000:
        return f"{num/10000:.1f}만"
    elif num >= 1000:
        return f"{num/1000:.1f}천"
    else:
        return str(num)

def create_message(channels_data):
    """텔레그램 메시지 생성"""
    lines = []
    lines.append("📊 YouTube 멀티채널 대시보드")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📈 전체 요약")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    total_48h = sum(d['rolling_48h'] for d in channels_data if d['rolling_48h'] is not None)
    total_60m = sum(d['hourly_change'] for d in channels_data if d['hourly_change'] is not None)
    
    if total_48h > 0:
        lines.append(f"48시간: +{format_number(total_48h)}")
    else:
        lines.append("48시간: +0")
    
    if total_60m > 0:
        lines.append(f"60분: +{format_number(total_60m)}")
    else:
        lines.append("60분: +0")
    
    lines.append("")
    
    for data in channels_data:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🎬 {data['name']}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"쇼츠: {data['shorts_count']}개 (90초 이하)")
        lines.append(f"전체 조회수: {format_number(data['total_views'])}회")
        
        if data['hourly_change'] is not None:
            lines.append(f"⏰ 60분: +{format_number(data['hourly_change'])}")
        else:
            lines.append("⏰ 60분: (대기)")
        
        if data['rolling_48h'] is not None:
            lines.append(f"📅 48시간: +{format_number(data['rolling_48h'])}")
        else:
            lines.append("📅 48시간: (대기)")
        
        if data['recent_video']:
            video = data['recent_video']
            lines.append(f"🎬 최근: \"{video['title']}\" | {format_number(video['viewCount'])}회")
        
        lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(lines)

def send_telegram(message, image_paths=[]):
    """텔레그램 전송"""
    for image_path in image_paths:
        if os.path.exists(image_path):
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': TELEGRAM_CHAT_ID}
                try:
                    requests.post(url, files=files, data=data, timeout=30)
                    print(f"✅ 이미지 전송: {os.path.basename(image_path)}")
                except Exception as e:
                    print(f"❌ 이미지 전송 실패: {e}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            print("✅ 텔레그램 전송 완료!")
        else:
            print(f"❌ 텔레그램 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 텔레그램 전송 오류: {e}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--telegram', action='store_true', help='텔레그램 전송')
    args = parser.parse_args()
    
    print("🎬 YouTube 멀티채널 대시보드 시작")
    print("📊 전체 쇼츠 추적 (90초 기준)")
    print("")
    
    channels = load_channels()
    history = load_history()
    now = datetime.now()
    
    channels_data = []
    
    for channel in channels:
        name = channel['name']
        channel_id = channel['id']
        
        print(f"{name} 수집 중...")
        
        videos = get_all_shorts(channel_id, max_pages=10)
        total_views = sum(v['viewCount'] for v in videos)
        
        print(f"✅ 쇼츠: {len(videos)}개 (90초 이하)")
        print(f"✅ 전체 조회수: {format_number(total_views)}회")
        print("")
        
        # 히스토리 계산
        hourly_change = None
        rolling_48h = None
        
        if name in history:
            prev_data = history[name]
            prev_views = prev_data.get('total_views', 0)
            hourly_change = total_views - prev_views
        
        recent_video = videos[0] if videos else None
        
        channels_data.append({
            'name': name,
            'shorts_count': len(videos),
            'total_views': total_views,
            'hourly_change': hourly_change,
            'rolling_48h': rolling_48h,
            'recent_video': recent_video
        })
        
        history[name] = {
            'total_views': total_views,
            'timestamp': now.isoformat()
        }
    
    save_history(history)
    
    message = create_message(channels_data)
    
    if args.telegram:
        send_telegram(message, [])
    else:
        print(message)
    
    print("✅ 완료!")

if __name__ == '__main__':
    main()
