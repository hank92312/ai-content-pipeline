import os
import glob
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    print("❌ 找不到 moviepy 套件，請執行: pip install moviepy")
    sys.exit(1)

# ============================================================
#  🎬 模組七：影片自動字幕 (Video Subtitles)
#  小花的AI情報站 - AI Content Pipeline
# ============================================================

VIDEOS_DIR  = "output_videos"
VOICES_DIR  = "output_voices"
SCRIPTS_DIR = "output_scripts"
FONT_PATH   = "C:\\Windows\\Fonts\\msjhbd.ttc"  # 微軟正黑體粗體

def create_subtitle_clip(text, keywords, duration, font_path=FONT_PATH, font_size=65, stroke_width=5):
    """
    使用 Pillow 動態繪製每一句短影音字幕。
    支援多色高亮 (關鍵字: 黃色, 驚嘆號: 紅色)，並回傳透明背景的 MoviePy ImageClip。
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"⚠️ 找不到字體 {font_path}，請確保 Windows 系統含有此字體。")
        # Fail-safe fallback (可能沒有中文支援)
        font = ImageFont.load_default()

    # 建立一塊透明畫布 (寬度吻合直式影片 1080，高度預留 400 供多行排列)
    img = Image.new("RGBA", (1080, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 建立每個字元的顏色對應表
    colors = ["white"] * len(text)
    
    # 1. 關鍵字標色為黃色 (#FFD700)
    for kw in keywords:
        if not kw: continue
        start = 0
        while True:
            idx = text.find(kw, start)
            if idx == -1: break
            for i in range(idx, idx + len(kw)):
                colors[i] = "#FFD700"
            start = idx + len(kw)
            
    # 2. 驚嘆號/問號/強調符號標色為紅色 (#FF3333)
    for i, c in enumerate(text):
        if c in ["!", "?", "！", "？", "🔥", "✨"]:
            colors[i] = "#FF3333"

    # 3. 處理自動換行與測量寬度
    lines = []
    current_line = []
    current_line_width = 0
    max_line_width = 950  # 左右留白
    
    for i, c in enumerate(text):
        # getbbox 回傳 (left, top, right, bottom)
        bbox = font.getbbox(c)
        cw = bbox[2] if bbox else font_size
        
        # 若目前行太寬，就換行
        if current_line_width + cw > max_line_width:
            lines.append(current_line)
            current_line = []
            current_line_width = 0
            
        current_line.append((c, colors[i], cw))
        current_line_width += cw
        
    if current_line:
        lines.append(current_line)
        
    # 4. 開始置中繪製
    start_y = 50
    for line in lines:
        line_w = sum(cw for _, _, cw in line)
        start_x = (1080 - line_w) // 2  # 水平置中
        
        for char, col, cw in line:
            # 繪製字體與黑色粗邊框
            draw.text((start_x, start_y), char, font=font, fill=col, stroke_width=stroke_width, stroke_fill="black")
            start_x += cw
        
        # 下一行的 Y 軸位移
        start_y += font_size + 20
        
    # 將 Pillow 圖片轉回 Numpy Array 交給 MoviePy
    clip = (ImageClip(np.array(img))
            .with_duration(duration))
            
    return clip

def main():
    print("========================================")
    print("  🎬 AI 影片動態字幕生成中心 (Subtitles)")
    print("========================================")

    # 尋找所有產出的影片檔 (不包含已經加上 subtitle_ 的)
    video_files = glob.glob(os.path.join(VIDEOS_DIR, "*.mp4"))
    video_files = [v for v in video_files if not v.endswith("_subtitled.mp4")]

    if not video_files:
        print(f"❌ 在 '{VIDEOS_DIR}/' 中找不到待上字幕的 mp4 檔。")
        print("   請確認 step6 已經執行完畢！")
        return

    for video_path in video_files:
        basename = os.path.basename(video_path).replace(".mp4", "")
        print(f"\n▶ 正在替影片上字幕：{basename}")
        
        subs_json_path = os.path.join(VOICES_DIR, f"{basename}_subs.json")
        script_json_path = os.path.join(SCRIPTS_DIR, f"{basename}.json")
        
        if not os.path.exists(subs_json_path):
            print(f"  ⚠️ 找不到對應的時間軸檔：{subs_json_path} (請重跑 step3)")
            continue

        # 讀取腳本解析出來的關鍵字
        keywords = []
        if os.path.exists(script_json_path):
            with open(script_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keywords = data.get("keywords", [])
                print(f"  🔠 找到重點關鍵字：{keywords}")
        
        # 讀取字幕時間軸
        with open(subs_json_path, 'r', encoding='utf-8') as f:
            subs_data = json.load(f)
            
        print(f"  📝 共計 {len(subs_data)} 句字幕要處理...")
        
        # 讀取原始影片
        video_clip = VideoFileClip(video_path)
        
        # 生成字幕列表
        subtitle_clips = []
        for sub in subs_data:
            text = sub["text"]
            start_t = sub["start"]
            duration = sub["duration"]
            
            # 使用 Pillow 產生高彩度自訂繪製字卡
            txt_clip = create_subtitle_clip(text, keywords, duration)
            
            # 將字卡安排在時間軸對應位置，並把它放在畫面下方 (y=1200左右，避免擋到右下角頭像)
            # 在 1080x1920 畫面中，主角通常在右下角 (y大約1000~1920)，如果字體畫布高度是400，可放置在大概 center, y=1400 處
            txt_clip = (txt_clip
                        .with_start(start_t)
                        .with_position(("center", 1400))) 
            
            subtitle_clips.append(txt_clip)

        print("  🎥 開始將動態字幕合成壓製至影片底層...")
        
        # CompositeVideoClip 把原影片放置在最底層，subtitle_clips 疊加在上面
        final_video = CompositeVideoClip([video_clip] + subtitle_clips)
        
        out_path = os.path.join(VIDEOS_DIR, f"{basename}_subtitled.mp4")
        
        success = False
        try:
            print("  ⚡ 嘗試使用 AMD GPU 硬體加速壓製...")
            final_video.write_videofile(out_path, fps=video_clip.fps, codec="h264_amf", audio_codec="aac", logger="bar")
            success = True
        except Exception as e:
            print(f"  ⚠️ AMD 硬解不支援此電腦 ({e})，切換至標準 CPU 模式...")

        if not success:
            final_video.write_videofile(out_path, fps=video_clip.fps, codec="libx264", audio_codec="aac", logger="bar")
        
        video_clip.close()
        final_video.close()
        
    print("\n🎉 所有動態特效字幕壓制完畢！(附帶 _subtitled.mp4)")

if __name__ == "__main__":
    main()
