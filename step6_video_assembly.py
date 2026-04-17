import os
import glob
import sys
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
#  🎬 模組六：影片自動生成與字幕壓製中心
#  小花的AI情報站 - AI Content Pipeline
# ============================================================

try:
    from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip
    import moviepy.video.fx as vfx
    import moviepy.audio.fx as afx
    import re
except ImportError:
    print("❌ 找不到 moviepy 套件，請執行: pip install moviepy")
    sys.exit(1)

# --- 路徑與相關設定 ---
VOICES_DIR  = "output_voices"
IMAGES_DIR  = "output_images"
VIDEOS_DIR  = "output_videos"
SCRIPTS_DIR = "output_scripts"
AVATAR_PATH = "sample.png"
FONT_PATH   = "C:\\Windows\\Fonts\\msjhbd.ttc"  # 微軟正黑體粗體

TARGET_RESOLUTION = (1080, 1920)  # 直式短影音 9:16
FPS = 24  # 預設幀率

def extract_image_index(filepath: str) -> int:
    """處理像 script_Finance_6_0.jpg 這樣的檔名，抽取出後面的數字，以作為排序基準"""
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    try:
        idx_str = name_no_ext.split("_")[-1]
        return int(idx_str)
    except ValueError:
        return 0

def create_subtitle_clip(text, keywords, duration, font_path=FONT_PATH, font_size=65, stroke_width=5):
    """
    使用 Pillow 動態繪製每一句短影音字幕。
    支援多色高亮 (關鍵字: 黃色, 驚嘆號: 紅色)，並回傳透明背景的 MoviePy ImageClip。
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"⚠️ 找不到字體 {font_path}，請確保 Windows 系統含有此字體。")
        font = ImageFont.load_default()

    img = Image.new("RGBA", (1080, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
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
    max_line_width = 950  
    
    for i, c in enumerate(text):
        bbox = font.getbbox(c)
        cw = bbox[2] if bbox else font_size
        
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
        start_x = (1080 - line_w) // 2
        
        for char, col, cw in line:
            draw.text((start_x, start_y), char, font=font, fill=col, stroke_width=stroke_width, stroke_fill="black")
            start_x += cw
        
        start_y += font_size + 20
        
    clip = (ImageClip(np.array(img))
            .with_duration(duration))
            
    return clip

def main():
    print("========================================")
    print("  🎬 AI 影片自動生成與字幕壓製中心")
    print("========================================")

    mode = 1
    if len(sys.argv) > 1 and sys.argv[1] == "--mode=2":
        mode = 2
    elif len(sys.argv) > 1 and sys.argv[1] == "--mode=3":
        mode = 3
    elif len(sys.argv) <= 1:
        print("\n請選擇影片製作模式：")
        print("1: 原模式 (自動分配生成的圖片和配音製作)")
        print("2: 素材模式 (從 assets 資料夾找取同新聞ID的素材製作影片)")
        print("3: 去主播素材模式 (素材模式，但不疊加 sample.png)")
        ans = input("請選擇 (1, 2 或 3，預設 1): ").strip()
        if ans == "2":
            mode = 2
        elif ans == "3":
            mode = 3


    os.makedirs(VIDEOS_DIR, exist_ok=True)
    voice_files = glob.glob(os.path.join(VOICES_DIR, "*_final.wav"))

    if not voice_files:
        print(f"❌ 在 '{VOICES_DIR}/' 中找不到 *_final.wav 音檔。")
        print("   請確認 step3 已經執行完畢！")
        return

    has_avatar = os.path.exists(AVATAR_PATH)
    if not has_avatar:
        print(f"⚠️ 找不到虛擬頭像檔 '{AVATAR_PATH}'，將純粹播放新聞配圖底檔。")

    for v_path in voice_files:
        basename = os.path.basename(v_path).replace("_final.wav", "")
        print(f"\n▶ 正在合成並上字幕：{basename}")
        
        audio_clip = AudioFileClip(v_path)
        audio_duration = audio_clip.duration
        
        # 根據 mode 分流
        if mode == 1:
            # 2. 尋找對應的背景圖
            pattern = os.path.join(IMAGES_DIR, f"{basename}_*.jpg")
            img_paths = glob.glob(pattern)
            
            if not img_paths:
                print(f"  ❌ 找不到對應此語音的背景圖片：{pattern}")
                print("     跳過這個腳本...")
                continue
                
            img_paths = sorted(img_paths, key=extract_image_index)
            time_per_image = audio_duration / len(img_paths)
            print(f"  🖼 找到 {len(img_paths)} 張背景圖，每張圖將顯示 {time_per_image:.1f} 秒...")
            
            image_clips = []
            for img_path in img_paths:
                clip = (ImageClip(img_path)
                        .with_duration(time_per_image)
                        .resized(TARGET_RESOLUTION))
                image_clips.append(clip)
                
            # 3. 組合背景片斷
            processed_clips = []
            for i, clip in enumerate(image_clips):
                if i > 0:
                    processed_clips.append(clip.with_effects([vfx.CrossFadeIn(1.0)]))
                else:
                    processed_clips.append(clip)
                    
            bg_clip = concatenate_videoclips(processed_clips, padding=-1.0, method="compose")
            bg_clip = bg_clip.with_audio(audio_clip) 
            
            final_clips = [bg_clip]
        elif mode in [2, 3]:
            # 2 & 3. 素材模式尋找對應的影片、圖片與音效
            m = re.search(r'_(\d+)$', basename)
            if not m:
                print(f"  ❌ 無法從 {basename} 解析新聞ID，跳過素材模式")
                continue
            news_id = m.group(1)
            
            asset_mp4 = os.path.join("assets", f"ID{news_id}.mp4")
            # 支援多種圖片格式作為轉場圖
            asset_jpg = None
            for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                test_path = os.path.join("assets", f"ID{news_id}{ext}")
                if os.path.exists(test_path):
                    asset_jpg = test_path
                    break
            asset_mp3 = os.path.join("assets", f"ID{news_id}.mp3")
            
            if not (os.path.exists(asset_mp4) and asset_jpg and os.path.exists(asset_mp3)):
                print(f"  ❌ 找不到 assets 相關素材 (ID{news_id}.mp4, 圖片, .mp3 需要同時存在)，跳過...")
                continue
                
            print(f"  🎨 使用短影音素材模式處理影片：ID{news_id}")
            
            # 使用 VideoFileClip 匯入並移除原本的音軌
            bg_video = VideoFileClip(asset_mp4).without_audio()
            # 播放至前 5 秒
            loop_dur = max(0, audio_duration - 5)
            bg_video_looped = bg_video.with_effects([vfx.Loop(duration=loop_dur)]).resized(TARGET_RESOLUTION)
            
            # 讀取轉場圖片並給定最後 5 秒
            bg_img = ImageClip(asset_jpg).with_duration(5).resized(TARGET_RESOLUTION).with_effects([vfx.CrossFadeIn(1.0)])
            
            # 組合循環影片和圖片
            bg_clip = concatenate_videoclips([bg_video_looped, bg_img], padding=-1.0, method="compose")
            
            # 放低背景音樂音量並加上原本的配音
            bgm_clip = AudioFileClip(asset_mp3).with_effects([
                afx.AudioLoop(duration=audio_duration),
                afx.MultiplyVolume(0.15)
            ])
            final_audio = CompositeAudioClip([bgm_clip, audio_clip]).with_duration(audio_duration)
            
            bg_clip = bg_clip.with_audio(final_audio)
            final_clips = [bg_clip]

        
        # 4. 疊加頭像 (模式 3 跳過)
        if has_avatar and mode != 3:
            print("  🙎‍♀️ 疊加動態/虛擬圖相 (此版本為靜態圖片 sample.png)...")
            avatar_clip = (ImageClip(AVATAR_PATH)
                           .resized(width=680)
                           .with_duration(audio_duration)
                           .with_position(("right", "bottom")))
            final_clips.append(avatar_clip)
            
        # 5. 處理動態字幕
        subs_json_path = os.path.join(VOICES_DIR, f"{basename}_subs.json")
        script_json_path = os.path.join(SCRIPTS_DIR, f"{basename}.json")
        
        if not os.path.exists(subs_json_path):
            print(f"  ⚠️ 找不到字幕時間軸檔：{subs_json_path}，本次影片將不會有字幕。")
        else:
            keywords = []
            if os.path.exists(script_json_path):
                with open(script_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    keywords = data.get("keywords", [])
            
            with open(subs_json_path, 'r', encoding='utf-8') as f:
                subs_data = json.load(f)
                
            print(f"  📝 處理中 {len(subs_data)} 句動態字幕...")
            
            for sub in subs_data:
                text = sub["text"]
                start_t = sub["start"]
                duration = sub["duration"]
                
                txt_clip = create_subtitle_clip(text, keywords, duration)
                txt_clip = (txt_clip
                            .with_start(start_t)
                            .with_position(("center", 1400))) 
                final_clips.append(txt_clip)
            
        # 6. 生成最終合成並輸出
        final_video = CompositeVideoClip(final_clips, size=TARGET_RESOLUTION)
        # 直接使用 _subtitled.mp4 名稱，不再產出無字幕版本
        out_path = os.path.join(VIDEOS_DIR, f"{basename}_subtitled.mp4")
        print(f"  🎥 開始寫入最終帶字幕影片: {out_path} ...\n")
        
        success = False
        # 1. 優先嘗試 AMD GPU 硬體加速 (AMF)
        try:
            print("  ⚡ 嘗試使用 AMD GPU 硬體加速編碼 (AMF)...")
            final_video.write_videofile(out_path, fps=FPS, codec="h264_amf", audio_codec="aac", logger="bar")
            success = True
        except Exception:
            print("  ⚠️ AMD AMF 不支援，嘗試下一項...")

        # 2. 次之嘗試 Intel QuickSync (QSV) 加速
        if not success:
            try:
                print("  ⚡ 嘗試使用 Intel QuickSync (QSV) 硬體加速編碼...")
                # QSV 使用 global_quality 來控制品質，20-25 為平衡點
                final_video.write_videofile(
                    out_path, 
                    fps=FPS, 
                    codec="h264_qsv", 
                    audio_codec="aac", 
                    logger="bar",
                    ffmpeg_params=["-global_quality", "25"]
                )
                success = True
            except Exception:
                print("  ⚠️ Intel QSV 不支援，切換至標準 CPU 模式...")

        # 3. 最後備案：標準 CPU 編碼 (libx264)
        if not success:
            print("  🐢 使用標準 CPU 模式進行編碼 (這可能需要較長時間)...")
            final_video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", logger="bar")
        
        audio_clip.close()
        final_video.close()
        
    print("\n🎉 所有影片合成暨字幕壓製完畢！")

if __name__ == "__main__":
    main()
