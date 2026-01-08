#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 멀티채널 대시보드 FINAL v4 - 전체 쇼츠 추적
- 채널의 "전체 쇼츠 영상" 조회수 합계로 정확한 계산
- 이미지 차트 생성
- 간소화된 메시지
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta
import argparse
import re
import isodate  # YouTube duration 파싱용

# matplotlib 설정
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    font_path = "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(font_path):
        font_manager.fontManager.addfont(font_path)
        rc('font', family='Malgun Gothic')
else:
    try:
        rc('font', family='DejaVu Sans')
    except:
        pass

plt.rcParams['axes.unicode_minus'] = False

# ==================== 설정 ====================
API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyA3MfhHkG1fhPEl04ZyDKS2IkFxyQGijvA")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8589679004:AAG8vsa2kh4MdDqWXjheCWGn6PbR1b0Y1SI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6046105835")
# ==============================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(SCRIPT_DIR, "channels.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "youtube_history_v4.json")
CHART_48H = os.path.join(SCRIPT_DIR, "chart_48h.png")
CHART_60MIN = os.path.join(SCRIPT_DIR, "chart_60min.png")

def load_channels():
    """채널 목록 로드"""
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    
    return [
        {"name": "배꼽나와", "id": "UCoLCO6_rNMT8EwUTvt3gsgw"},
        {"name": "심장톡톡", "id": "UC5kAxeHTWkWk1QJeRWTtCsg"},
        {"name": "포동무비(스릴러)", "id": "UC1vLkNS0rFJQEZn78RbkpaQ"},
        {"name": "힐링토끼", "id": "UCChsmm5ABoPyYoe6VX6vXnQ"},
        {"name": "도도tv(원영)", "id": "UCfvKR_5YIZT4K3qDKezMuPw"},
        {"name": "숏숏냥이(참교육)", "id": "UCb58xO2kVwoS8NKyY60tzCQ"},
        {"name": "사이다tv", "id": "UCQVgBc41oUaWALP_opNH1FQ"},
        {"name": "킬링타임즈", "id": "UCpT2-M3WUF5U7-nh-1gq_aA"},
        {"name": "무비삼촌", "id": "UCFjfiKm3uW3E57MzpKWZqpg"}
    ]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_all_shorts(channel_id):
    """채널의 전체 쇼츠 영상 가져오기"""
    all_videos = []
    page_token = None
    max_pages = 20  # 최대 1000개 영상 (50 x 20)
    
    print(f"  📹 전체 쇼츠 수집 중...", end="", flush=True)
    
    for page in range(max_pages):
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": 50,
            "key": API_KEY
        }
        
        if page_token:
            params["pageToken"] = page_token
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
            
            if not video_ids:
                break
            
            # 영상 상세 정보 가져오기 (duration 포함)
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            videos_params = {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": API_KEY
            }
            
            videos_response = requests.get(videos_url, params=videos_params, timeout=15)
            videos_response.raise_for_status()
            videos_data = videos_response.json()
            
            # 쇼츠 필터링 (60초 이하)
            for item in videos_data.get("items", []):
                try:
                    duration_str = item["contentDetails"]["duration"]
                    duration = isodate.parse_duration(duration_str)
                    duration_seconds = duration.total_seconds()
                    
                    # 쇼츠: 60초 이하
                    if duration_seconds <= 90:
                        video_id = item["id"]
                        title = item["snippet"]["title"]
                        title_clean = re.sub(r'#.*$', '', title).strip()
                        title_short = title_clean[:15] + "..." if len(title_clean) > 15 else title_clean
                        
                        view_count = int(item["statistics"].get("viewCount", 0))
                        
                        all_videos.append({
                            "videoId": video_id,
                            "title": title_short,
                            "title_full": title_clean,
                            "viewCount": view_count,
                            "duration": duration_seconds
                        })
                except:
                    continue
            
            print(".", end="", flush=True)
            
            # 다음 페이지
            page_token = data.get("nextPageToken")
            if not page_token:
                break
                
        except Exception as e:
            print(f"\n  ⚠️ 페이지 {page+1} 오류: {e}")
            break
    
    print(f" 완료! ({len(all_videos)}개 쇼츠)")
    return all_videos

def format_number(num):
    if num >= 10000:
        return f"{num/10000:.1f}만"
    elif num >= 1000:
        return f"{num/1000:.1f}천"
    else:
        return str(num)

def create_chart_image(data, title, filename, bar_color='#00A8E1'):
    """막대 그래프 이미지 생성"""
    if not data:
        return
    
    fig, ax = plt.subplots(figsize=(12, 4), facecolor='#2C2F33')
    ax.set_facecolor('#2C2F33')
    
    labels = [item['label'] for item in data]
    values = [item['value'] for item in data]
    
    bars = ax.bar(range(len(labels)), values, color=bar_color, alpha=0.8)
    
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', color='white', fontsize=9)
    ax.set_ylabel('조회수 증가', color='white', fontsize=11)
    ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=20)
    
    ax.grid(axis='y', alpha=0.3, linestyle='--', color='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('gray')
    ax.spines['bottom'].set_color('gray')
    ax.tick_params(colors='white')
    
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'+{format_number(value)}',
                ha='center', va='bottom', color='white', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=100, facecolor='#2C2F33')
    plt.close()
    
    print(f"  ✅ 차트 생성: {filename}")

def collect_data():
    print(f"\n{'='*50}")
    print(f"🎬 YouTube 멀티채널 대시보드 FINAL v4")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    channels = load_channels()
    history = load_history()
    
    now = datetime.now()
    now_key = now.strftime("%Y-%m-%dT%H:00:00")
    
    all_data = []
    surge_videos = []
    hourly_totals = {}
    
    for channel in channels:
        channel_name = channel["name"]
        channel_id = channel["id"]
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {channel_name}")
        
        # 전체 쇼츠 가져오기
        all_shorts = get_all_shorts(channel_id)
        
        if not all_shorts:
            print(f"  ❌ 쇼츠 없음")
            continue
        
        # 전체 쇼츠 조회수 합계 (정확!)
        total_views = sum(video["viewCount"] for video in all_shorts)
        
        print(f"  📊 전체 쇼츠 조회수: {format_number(total_views)}회")
        
        # 히스토리 저장
        if channel_id not in history:
            history[channel_id] = {}
        
        history[channel_id][now_key] = {
            "total_views": total_views,
            "shorts_count": len(all_shorts)
        }
        
        # 60분 변화량 계산
        sorted_times = sorted(history[channel_id].keys(), reverse=True)
        
        hourly_change = None
        rolling_48h = None
        
        if len(sorted_times) >= 2:
            current_data = history[channel_id][sorted_times[0]]
            previous_data = history[channel_id][sorted_times[1]]
            
            hourly_change = current_data["total_views"] - previous_data["total_views"]
        
        # 48시간 변화량
        if len(sorted_times) >= 48:
            hours_48_data = history[channel_id][sorted_times[47]]
            rolling_48h = current_data["total_views"] - hours_48_data["total_views"]
        
        # 개별 영상 급등 감지 (상위 50개만 추적)
        for video in all_shorts[:50]:
            video_id = video["videoId"]
            video_key = f"{channel_id}_{video_id}"
            
            if video_key not in history:
                history[video_key] = {}
            
            history[video_key][now_key] = video["viewCount"]
            
            video_times = sorted(history[video_key].keys(), reverse=True)
            
            if len(video_times) >= 2:
                video_current = history[video_key][video_times[0]]
                video_previous = history[video_key][video_times[1]]
                
                video_change = video_current - video_previous
                video_change_percent = (video_change / video_previous * 100) if video_previous > 0 else 0
                
                if video_change_percent >= 50 and video_change > 0:
                    surge_videos.append({
                        "channel_name": channel_name,
                        "video_title": video["title_full"],
                        "video_views": video_current,
                        "video_change": video_change,
                        "change_percent": video_change_percent
                    })
        
        # 48시간 추이용
        for timestamp in sorted_times:
            if timestamp not in hourly_totals:
                hourly_totals[timestamp] = 0
            hourly_totals[timestamp] += history[channel_id][timestamp]["total_views"]
        
        data = {
            "name": channel_name,
            "id": channel_id,
            "total_views": total_views,
            "shorts_count": len(all_shorts),
            "hourly_change": hourly_change,
            "rolling_48h": rolling_48h,
            "recent_video": all_shorts[0] if all_shorts else None
        }
        
        all_data.append(data)
        print(f"  ✅ 완료\n")
    
    # 히스토리 저장
    save_history(history)
    
    # 전체 합계 계산
    sorted_hourly_times = sorted(hourly_totals.keys(), reverse=True)
    
    total_60min = 0
    total_48h = 0
    
    if len(sorted_hourly_times) >= 2:
        total_60min = hourly_totals[sorted_hourly_times[0]] - hourly_totals[sorted_hourly_times[1]]
    
    if len(sorted_hourly_times) >= 48:
        total_48h = hourly_totals[sorted_hourly_times[0]] - hourly_totals[sorted_hourly_times[47]]
    
    # 급등 영상 정렬
    surge_videos.sort(key=lambda x: x["change_percent"], reverse=True)
    
    # 차트 생성
    print(f"📊 차트 생성 중...")
    
    # 48시간 차트
    chart_48h_data = []
    if len(sorted_hourly_times) >= 48:
        for i in range(47, -1, -6):
            if i > 0 and i < len(sorted_hourly_times):
                time_label = sorted_hourly_times[i][-8:-3]
                current = hourly_totals[sorted_hourly_times[i]]
                previous = hourly_totals[sorted_hourly_times[min(i+1, len(sorted_hourly_times)-1)]]
                change = current - previous
                if change > 0:
                    chart_48h_data.append({"label": time_label, "value": change})
    
    if chart_48h_data:
        create_chart_image(chart_48h_data, "48시간 추이", CHART_48H, bar_color='#00A8E1')
    
    # 60분 차트
    chart_60min_data = []
    for data in all_data:
        if data["hourly_change"] and data["hourly_change"] > 0:
            chart_60min_data.append({
                "label": data["name"],
                "value": data["hourly_change"]
            })
    
    if chart_60min_data:
        create_chart_image(chart_60min_data, "60분 변화량", CHART_60MIN, bar_color='#43B581')
    
    print(f"\n{'='*50}")
    print(f"✅ 완료!")
    print(f"{'='*50}\n")
    
    return {
        "all_data": all_data,
        "total_60min": total_60min,
        "total_48h": total_48h,
        "surge_videos": surge_videos,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "has_48h_chart": os.path.exists(CHART_48H),
        "has_60min_chart": os.path.exists(CHART_60MIN)
    }

def format_telegram_message(result):
    lines = []
    
    lines.append(f"📊 전체 요약 ({result['timestamp']})")
    lines.append("")
    lines.append(f"📈 48시간: +{format_number(result['total_48h'])}")
    lines.append(f"⏱️ 60분: +{format_number(result['total_60min'])}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if result['surge_videos']:
        lines.append("")
        lines.append("🔥 급등 영상 (60분 +50%)")
        lines.append("")
        
        for surge in result['surge_videos'][:5]:
            lines.append(f"📺 {surge['channel_name']}")
            lines.append(f"   \"{surge['video_title']}\"")
            lines.append(f"   60분: +{format_number(surge['video_change'])} (+{surge['change_percent']:.0f}% 🔥)")
            lines.append(f"   총: {format_number(surge['video_views'])}회")
            lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("📺 개별 채널")
    lines.append("")
    
    for data in result['all_data']:
        lines.append(f"📺 {data['name']} (쇼츠 {data['shorts_count']}개)")
        
        if data['hourly_change'] is not None:
            lines.append(f"⏱️ 60분: +{format_number(data['hourly_change'])}")
        else:
            lines.append(f"⏱️ 60분: (대기)")
        
        if data['rolling_48h'] is not None:
            lines.append(f"📅 48시간: +{format_number(data['rolling_48h'])}")
        else:
            lines.append(f"📅 48시간: (대기)")
        
        if data['recent_video']:
            video = data['recent_video']
            lines.append(f"🎬 최근: \"{video['title']}\" | {format_number(video['viewCount'])}회")
        
        lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ 다음: {(datetime.now() + timedelta(hours=1)).strftime('%H:00')}")
    
    return "\n".join(lines)

def send_telegram(message, image_paths=[]):
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
                    print(f"❌ 이미지 실패: {e}")
    
    # 텍스트 전송
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        print("✅ 메시지 전송 완료!")
        return True
    except Exception as e:
        print(f"❌ 전송 실패: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()
    
    result = collect_data()
    
    if args.telegram:
        message = format_telegram_message(result)
        
        images = []
        if result['has_48h_chart']:
            images.append(CHART_48H)
        if result['has_60min_chart']:
            images.append(CHART_60MIN)
        
        send_telegram(message, images)

if __name__ == "__main__":
    main()
