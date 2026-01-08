#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 멀티채널 대시보드 FINAL
- 90초 기준 쇼츠 추적
- 급등 영상 알림
- 텔레그램 자동 전송
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
HISTORY_FILE = os.path.join(SCRIPT_DIR, 'youtube_history.json')
CHART_48H = os.path.join(SCRIPT_DIR, 'chart_48h.png')
CHART_60MIN = os.path.join(SCRIPT_DIR, 'chart_60min.png')

def load_channels():
    """채널 목록 (7개)"""
    return [
        {'name': '배꼽나와', 'id': 'UCoLCO6_rNMT8EwUTvt3gsgw'},
        {'name': '심장톡톡', 'id': 'UC5kAxeHTWkWk1QJeRWTtCsg'},
        {'name': '포동무비(스릴러)', 'id': 'UC1vLkNS0rFJQEZn78RbkpaQ'},
        {'name': '힐링토끼', 'id': 'UCChsmm5ABoPyYoe6VX6vXnQ'},
        {'name': '도도tv(참교육)', 'id': 'UCfvKR_5YIZT4K3qDKezMuPw'},
        {'name': '숏숏냥이(참교육)', 'id': 'UCb58xO2kVwoS8NKyY60tzCQ'},
        {'name': '사이다tv', 'id': 'UCQVgBc41oUaWALP_opNH1FQ'}
    ]

def load_history():
    """히스토리 로드"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
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
                print(f"❌ API 오류 {response.status_code}")
                break
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                break
            
            video_ids = [item['id']['videoId'] for item in items]
            
            # 비디오 상세 정보
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
                    
                    # 90초 이하만 쇼츠
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

def create_chart(data, title, filename, color):
    """차트 생성"""
    if not data:
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    labels = [d['label'] for d in data]
    values = [d['value'] for d in data]
    
    ax.barh(labels, values, color=color)
    ax.set_xlabel('조회수 증가')
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()

def create_message(channels_data, surge_videos, total_48h, total_60m):
    """텔레그램 메시지 생성"""
    lines = []
    lines.append(f"📊 전체 요약 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    lines.append("")
    
    if total_48h > 0:
        lines.append(f"📈 48시간: +{format_number(total_48h)}")
    else:
        lines.append("📈 48시간: +0")
    
    if total_60m > 0:
        lines.append(f"⏱️ 60분: +{format_number(total_60m)}")
    else:
        lines.append("⏱️ 60분: +0")
    
    # 급등 영상
    if surge_videos:
        lines.append("")
        lines.append("🔥 급등 영상 (60분 +50%)")
        lines.append("")
        
        for surge in surge_videos[:5]:
            lines.append(f"📺 {surge['channel']}")
            lines.append(f"   \"{surge['title']}\"")
            lines.append(f"   60분: +{format_number(surge['change'])} (+{surge['percent']:.0f}% 🔥)")
            lines.append(f"   총: {format_number(surge['views'])}회")
            lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("📺 개별 채널")
    lines.append("")
    
    for data in channels_data:
        lines.append(f"📺 {data['name']} (쇼츠 {data['shorts_count']}개)")
        
        if data['hourly_change'] is not None:
            lines.append(f"60분: +{format_number(data['hourly_change'])}")
        else:
            lines.append("60분: (대기)")
        
        if data['rolling_48h'] is not None:
            lines.append(f"48시간: +{format_number(data['rolling_48h'])}")
        else:
            lines.append("48시간: (대기)")
        
        if data['recent_video']:
            video = data['recent_video']
            title_short = video['title'][:30] + "..." if len(video['title']) > 30 else video['title']
            lines.append(f"최근: \"{title_short}\" | {format_number(video['viewCount'])}회")
        
        lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(lines)

def send_telegram(message, image_paths=[]):
    """텔레그램 전송"""
    # 이미지 전송
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
    
    # 메시지 전송
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
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
    
    print("🎬 YouTube 멀티채널 대시보드")
    print("📊 90초 기준 쇼츠 추적")
    print("")
    
    channels = load_channels()
    history = load_history()
    now = datetime.now()
    
    channels_data = []
    surge_videos = []
    total_60m = 0
    total_48h = 0
    
    for channel in channels:
        name = channel['name']
        channel_id = channel['id']
        
        print(f"{name} 수집 중...")
        
        videos = get_all_shorts(channel_id, max_pages=10)
        
        print(f"✅ 쇼츠: {len(videos)}개")
        
        # 히스토리 계산
        hourly_change = None
        rolling_48h = None
        
        if name in history:
            prev_data = history[name]
            
            # 60분 변화량
            if 'videos' in prev_data:
                prev_videos = {v['videoId']: v['viewCount'] for v in prev_data['videos']}
                current_total = sum(v['viewCount'] for v in videos)
                prev_total = sum(prev_videos.values())
                hourly_change = current_total - prev_total
                total_60m += hourly_change if hourly_change else 0
                
                # 급등 영상 찾기 (60분 +50%)
                for video in videos[:50]:
                    vid = video['videoId']
                    current_views = video['viewCount']
                    if vid in prev_videos:
                        prev_views = prev_videos[vid]
                        if prev_views > 0:
                            change = current_views - prev_views
                            percent = (change / prev_views) * 100
                            if percent >= 50 and change > 0:
                                surge_videos.append({
                                    'channel': name,
                                    'title': video['title'],
                                    'change': change,
                                    'percent': percent,
                                    'views': current_views
                                })
        
        recent_video = videos[0] if videos else None
        
        channels_data.append({
            'name': name,
            'shorts_count': len(videos),
            'hourly_change': hourly_change,
            'rolling_48h': rolling_48h,
            'recent_video': recent_video
        })
        
        # 히스토리 저장
        history[name] = {
            'videos': videos[:50],
            'timestamp': now.isoformat()
        }
    
    # 급등 영상 정렬
    surge_videos.sort(key=lambda x: x['change'], reverse=True)
    
    save_history(history)
    
    # 메시지 생성
    message = create_message(channels_data, surge_videos, total_48h, total_60m)
    
    # 차트 생성
    chart_60min_data = []
    for data in channels_data:
        if data['hourly_change'] and data['hourly_change'] > 0:
            chart_60min_data.append({
                'label': data['name'],
                'value': data['hourly_change']
            })
    
    if chart_60min_data:
        create_chart(chart_60min_data, "60분 변화량", CHART_60MIN, '#43B581')
    
    if args.telegram:
        images = []
        if os.path.exists(CHART_60MIN):
            images.append(CHART_60MIN)
        if os.path.exists(CHART_48H):
            images.append(CHART_48H)
        send_telegram(message, images)
    else:
        print(message)
    
    print("✅ 완료!")

if __name__ == '__main__':
    main()
