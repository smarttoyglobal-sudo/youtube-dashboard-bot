#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 멀티채널 대시보드 FINAL v4
- GitHub 자동 커밋으로 히스토리 영구 저장
- 90초 기준 쇼츠 추적
- 급등 영상 알림
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
import re
import isodate
import subprocess

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
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # GitHub Personal Access Token
GITHUB_REPO = os.getenv('GITHUB_REPO', 'smarttoyglobal-sudo/youtube-dashboard-bot')  # username/repo

# 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, 'youtube_history_v4.json')
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

def download_history_from_github():
    """GitHub에서 히스토리 파일 다운로드"""
    if not GITHUB_TOKEN:
        print("⚠️ GITHUB_TOKEN 없음 - 로컬 파일 사용")
        return load_history_local()
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/youtube_history_v4.json"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3.raw'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✅ GitHub에서 히스토리 다운로드 성공")
            return json.loads(response.text)
        elif response.status_code == 404:
            print("📝 GitHub에 히스토리 없음 - 새로 생성")
            return {}
        else:
            print(f"⚠️ GitHub 다운로드 실패 ({response.status_code}) - 로컬 사용")
            return load_history_local()
    except Exception as e:
        print(f"⚠️ GitHub 다운로드 오류: {e} - 로컬 사용")
        return load_history_local()

def load_history_local():
    """로컬 히스토리 파일 로드"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_history_local(history):
    """로컬 히스토리 파일 저장"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def upload_history_to_github(history):
    """GitHub에 히스토리 파일 업로드 (자동 커밋)"""
    if not GITHUB_TOKEN:
        print("⚠️ GITHUB_TOKEN 없음 - GitHub 업로드 생략")
        return False
    
    try:
        # 로컬에 먼저 저장
        save_history_local(history)
        
        # GitHub API로 파일 업로드
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/youtube_history_v4.json"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 기존 파일 SHA 가져오기 (업데이트 시 필요)
        get_response = requests.get(url, headers=headers, timeout=30)
        sha = None
        if get_response.status_code == 200:
            sha = get_response.json().get('sha')
        
        # 파일 내용을 base64로 인코딩
        import base64
        content = json.dumps(history, ensure_ascii=False, indent=2)
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # 커밋 데이터
        commit_data = {
            'message': f'Update history: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'content': content_base64,
            'branch': 'main'
        }
        
        if sha:
            commit_data['sha'] = sha
        
        # 업로드
        put_response = requests.put(url, headers=headers, json=commit_data, timeout=30)
        
        if put_response.status_code in [200, 201]:
            print("✅ GitHub 업로드 성공!")
            return True
        else:
            print(f"❌ GitHub 업로드 실패 ({put_response.status_code}): {put_response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ GitHub 업로드 오류: {e}")
        return False

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
                print(f"  ❌ API 오류 {response.status_code}")
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
            print(f"  ❌ 수집 오류: {e}")
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
            title_short = surge['title'][:30] + "..." if len(surge['title']) > 30 else surge['title']
            lines.append(f"   \"{title_short}\"")
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
    print("💾 GitHub 자동 커밋")
    print("")
    
    channels = load_channels()
    
    # GitHub에서 히스토리 다운로드
    print("📥 GitHub에서 히스토리 다운로드 중...")
    history = download_history_from_github()
    
    now = datetime.now()
    now_key = now.strftime("%Y-%m-%d_%H:00")
    
    channels_data = []
    surge_videos = []
    total_60m = 0
    total_48h = 0
    
    for channel in channels:
        name = channel['name']
        channel_id = channel['id']
        
        print(f"{name} 수집 중...")
        
        videos = get_all_shorts(channel_id, max_pages=10)
        total_views = sum(v['viewCount'] for v in videos)
        
        print(f"✅ 쇼츠: {len(videos)}개, 총 조회수: {format_number(total_views)}회")
        
        # 히스토리 저장
        if channel_id not in history:
            history[channel_id] = {}
        
        history[channel_id][now_key] = {
            'total_views': total_views,
            'shorts_count': len(videos),
            'videos': videos[:50]  # 상위 50개만 저장
        }
        
        # 60분 변화량 계산
        sorted_times = sorted(history[channel_id].keys(), reverse=True)
        hourly_change = None
        rolling_48h = None
        
        if len(sorted_times) >= 2:
            current = history[channel_id][sorted_times[0]]
            previous = history[channel_id][sorted_times[1]]
            hourly_change = current['total_views'] - previous['total_views']
            total_60m += hourly_change if hourly_change else 0
            
            # 급등 영상 찾기
            if 'videos' in previous:
                prev_videos = {v['videoId']: v['viewCount'] for v in previous.get('videos', [])}
                for video in videos[:50]:
                    vid = video['videoId']
                    if vid in prev_videos:
                        prev_views = prev_videos[vid]
                        if prev_views > 0:
                            change = video['viewCount'] - prev_views
                            percent = (change / prev_views) * 100
                            if percent >= 50 and change > 0:
                                surge_videos.append({
                                    'channel': name,
                                    'title': video['title'],
                                    'change': change,
                                    'percent': percent,
                                    'views': video['viewCount']
                                })
        
        # 48시간 변화량
        if len(sorted_times) >= 48:
            hours_48 = history[channel_id][sorted_times[47]]
            rolling_48h = history[channel_id][sorted_times[0]]['total_views'] - hours_48['total_views']
            total_48h += rolling_48h if rolling_48h else 0
        
        recent_video = videos[0] if videos else None
        
        channels_data.append({
            'name': name,
            'shorts_count': len(videos),
            'hourly_change': hourly_change,
            'rolling_48h': rolling_48h,
            'recent_video': recent_video
        })
    
    # 급등 영상 정렬
    surge_videos.sort(key=lambda x: x['change'], reverse=True)
    
    # GitHub에 업로드
    print("")
    print("📤 GitHub에 히스토리 업로드 중...")
    upload_history_to_github(history)
    
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
    
    print("")
    print("✅ 완료!")

if __name__ == '__main__':
    main()
