import os
import glob
import sys
import json
import numpy as np
import config
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
VOICES_DIR  = config.OUTPUT_VOICES
IMAGES_DIR  = config.OUTPUT_IMAGES
VIDEOS_DIR  = config.OUTPUT_VIDEOS
SCRIPTS_DIR = config.OUTPUT_SCRIPTS
AVATAR_PATH = config.ASSETS_DIR + "/sample.png"
if not os.path.exists(AVATAR_PATH):
    AVATAR_PATH = "sample.png" # Fallback to root if not in assets
FONT_PATH   = "C:\\Windows\\Fonts\\msjhbd.ttc"  # 微軟正黑體粗體

TARGET_RESOLUTION = (1080, 1920)  # 直式短影音 9:16
FPS = 24  # 預設幀率

def extract_file_index(filepath: str) -> int:
    """處理像 script_Finance_6_0.jpg 或 ID6_1.mp4 這樣的檔名，抽取出後面的數字，以作為排序基準"""
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    try:
        # 尋找最後一個底線後的數字
        parts = name_no_ext.split("_")
        if len(parts) > 1:
            return int(parts[-1])
        return 0
    except ValueError:
        return 0

def create_subtitle_clip(text, keywords, duration, font_path=FONT_PATH, font_size=58, stroke_width=5):
    """
    使用 Pillow 動態繪製每一句短影音字幕。
    支援多色高亮 (關鍵字: 黃色, 驚嘆號: 紅色)，並回傳透明背景的 MoviePy ImageClip。
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"⚠️ 找不到字體 {font_path}，請確保 Windows 系統含有此字體。")
        font = ImageFont.load_default()

    img = Image.new("RGBA", (1080, 600), (0, 0, 0, 0))
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
    custom_video = 0  # 0: 不增加, 1: 素材(去聲)
    custom_image = 0  # 0: 不增加, 1: 素材, 2: 模組生成
    custom_anchor = 0 # 0: 不加, 1: 加上
    custom_music = 0  # 0: 不增加, 1: 素材(降音)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--mode=2":
            mode = 2
        elif sys.argv[1] == "--mode=3":
            mode = 3
        elif sys.argv[1] == "--mode=4":
            mode = 4
    elif len(sys.argv) <= 1:
        print("\n請選擇影片製作模式：")
        print("1: 原模式 (自動分配生成的圖片和配音製作)")
        print("2: 素材模式 (從 assets 資料夾找取同新聞ID的素材製作影片)")
        print("3: 去主播素材模式 (素材模式，但不疊加 sample.png)")
        print("4: 客製化模式 (自由選擇各項來源)")
        ans = input("請選擇 (1, 2, 3 或 4，預設 1): ").strip()
        if ans == "2":
            mode = 2
        elif ans == "3":
            mode = 3
        elif ans == "4":
            mode = 4
            print("\n【客製化模式設定】")
            print("▶ 影片來源：")
            print("  1: 從素材資料夾 (去除本身聲音)")
            print("  0: 不增加影片")
            cv = input("請選擇 (預設 1): ").strip()
            custom_video = 0 if cv == "0" else 1
            
            print("\n▶ 圖片來源：")
            print("  1: 從素材資料夾")
            print("  2: 模組生成 (output_images)")
            print("  0: 不增加圖片")
            ci = input("請選擇 (預設 1): ").strip()
            custom_image = int(ci) if ci in ["0", "1", "2"] else 1
            
            print("\n▶ 主播圖片 (sample.png)：")
            print("  1: 加上")
            print("  0: 不加上")
            ca = input("請選擇 (預設 1): ").strip()
            custom_anchor = 0 if ca == "0" else 1

            print("\n▶ 音樂來源：")
            print("  1: 從素材資料夾 (降低音量作為 BGM)")
            print("  0: 不增加音樂")
            cm = input("請選擇 (預設 1): ").strip()
            custom_music = 0 if cm == "0" else 1


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
        
        # 初始化素材變數，確保每輪循環都能正確釋放
        bgm_clip = None
        bg_video = None
        
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
                
            img_paths = sorted(img_paths, key=extract_file_index)
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
            
            asset_mp3 = os.path.join("assets", f"ID{news_id}.mp3")
            
            # --- 搜尋影片素材 ---
            asset_video_paths = []
            for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                # 找序號影片 ID6_1.mp4, ID6_2.mp4...
                pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                asset_video_paths.extend(glob.glob(pattern))
            
            if not asset_video_paths:
                # 沒找到序號影片，改找單張 ID6.mp4
                for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                    test_path = os.path.join("assets", f"ID{news_id}{ext}")
                    if os.path.exists(test_path):
                        asset_video_paths = [test_path]
                        break
            
            asset_video_paths = sorted(asset_video_paths, key=extract_file_index)

            # --- 搜尋圖片素材 ---
            asset_img_paths = []
            for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                asset_img_paths.extend(glob.glob(pattern))
            
            if not asset_img_paths:
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    test_path = os.path.join("assets", f"ID{news_id}{ext}")
                    if os.path.exists(test_path):
                        asset_img_paths = [test_path]
                        break
            
            asset_img_paths = sorted(asset_img_paths, key=extract_file_index)
            
            # 檢查是否有任何影像素材 (影片或圖片)
            if not asset_video_paths and not asset_img_paths:
                print(f"  ❌ 找不到 assets 相關影像素材 (ID{news_id}.*), 跳過...")
                continue
                
            print(f"  🎨 使用素材模式處理影片：ID{news_id} (找到 {len(asset_video_paths)} 個影片, {len(asset_img_paths)} 張圖片)")
            
            # 準備音訊 (BGM 是選配)
            if os.path.exists(asset_mp3):
                bgm_clip = AudioFileClip(asset_mp3)
                if bgm_clip.duration is not None and bgm_clip.duration < audio_duration:
                    bgm_clip = bgm_clip.with_effects([
                        afx.AudioLoop(duration=audio_duration),
                        afx.MultiplyVolume(config.BGM_VOLUME)
                    ])
                else:
                    bgm_clip = bgm_clip.with_duration(audio_duration).with_effects([
                        afx.MultiplyVolume(config.BGM_VOLUME)
                    ])
                final_audio = CompositeAudioClip([bgm_clip, audio_clip]).with_duration(audio_duration)
            else:
                final_audio = audio_clip

            # --- 準備影像底圖 ---
            if asset_video_paths:
                video_clips = []
                for v_p in asset_video_paths:
                    try:
                        vc = VideoFileClip(v_p).without_audio().resized(TARGET_RESOLUTION)
                        video_clips.append(vc)
                    except Exception as e:
                        print(f"  ⚠️ 無法讀取影片 {v_p}: {e}")
                
                if video_clips:
                    # 串接所有影片
                    combined_video = concatenate_videoclips(video_clips, method="compose")
                    
                    if len(asset_img_paths) > 0:
                        # 有影片 + 有圖片 => 影片播到最後5秒接圖片
                        loop_dur = max(0, audio_duration - 5)
                        bg_video_looped = combined_video.with_effects([vfx.Loop(duration=loop_dur)])
                        bg_img = ImageClip(asset_img_paths[0]).with_duration(5).resized(TARGET_RESOLUTION).with_effects([vfx.CrossFadeIn(1.0)])
                        bg_clip = concatenate_videoclips([bg_video_looped, bg_img], padding=-1.0, method="compose")
                    else:
                        # 只有影片 => 直接 Loop 到滿
                        bg_clip = combined_video.with_effects([vfx.Loop(duration=audio_duration)])
                else:
                    # 如果讀取失敗回退到純圖片
                    bg_clip = None
            else:
                bg_clip = None

            # 如果沒影片或讀取失敗，使用圖片
            if bg_clip is None and asset_img_paths:
                if len(asset_img_paths) > 1:
                    time_per_image = audio_duration / len(asset_img_paths)
                    image_clips = []
                    for i, img_path in enumerate(asset_img_paths):
                        clip = ImageClip(img_path).with_duration(time_per_image).resized(TARGET_RESOLUTION)
                        if i > 0: clip = clip.with_effects([vfx.CrossFadeIn(1.0)])
                        image_clips.append(clip)
                    bg_clip = concatenate_videoclips(image_clips, padding=-1.0, method="compose")
                else:
                    bg_clip = ImageClip(asset_img_paths[0]).with_duration(audio_duration).resized(TARGET_RESOLUTION)

            bg_clip = bg_clip.with_audio(final_audio)
            final_clips = [bg_clip]

        elif mode == 4:
            m = re.search(r'_(\d+)$', basename)
            news_id = m.group(1) if m else None
            
            print(f"  🎨 使用客製化模式處理影片：{basename}")
            
            # --- 搜尋影片素材 ---
            asset_video_paths = []
            if custom_video == 1 and news_id:
                for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                    pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                    asset_video_paths.extend(glob.glob(pattern))
                
                if not asset_video_paths:
                    for ext in [".mp4", ".mov", ".mkv", ".avi"]:
                        test_path = os.path.join("assets", f"ID{news_id}{ext}")
                        if os.path.exists(test_path):
                            asset_video_paths = [test_path]
                            break
                
                asset_video_paths = sorted(asset_video_paths, key=extract_file_index)
            
            # --- 準備影片底圖 ---
            bg_video_clip = None
            if asset_video_paths:
                video_clips = []
                for v_p in asset_video_paths:
                    try:
                        vc = VideoFileClip(v_p).without_audio().resized(TARGET_RESOLUTION)
                        video_clips.append(vc)
                    except: pass
                if video_clips:
                    bg_video_clip = concatenate_videoclips(video_clips, method="compose")

            # --- 準備圖片序列 ---
            img_clip_list = []
            if custom_image == 1 and news_id:
                asset_img_paths = []
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    pattern = os.path.join("assets", f"ID{news_id}_*{ext}")
                    asset_img_paths.extend(glob.glob(pattern))
                
                if not asset_img_paths:
                    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                        test_path = os.path.join("assets", f"ID{news_id}{ext}")
                        if os.path.exists(test_path):
                            asset_img_paths = [test_path]
                            break
                
                if asset_img_paths:
                    img_clip_list = sorted(asset_img_paths, key=extract_file_index)
            elif custom_image == 2:
                pattern = os.path.join(IMAGES_DIR, f"{basename}_*.jpg")
                mod_imgs = glob.glob(pattern)
                if mod_imgs:
                    img_clip_list = sorted(mod_imgs, key=extract_file_index)
                else:
                    print(f"  ⚠️ 無法找到模組生成圖片 {pattern}")
                    
            # --- 組合影像底圖 ---
            if bg_video_clip is not None:
                if len(img_clip_list) > 0:
                    # 有影片 + 有圖片 => 影片播到最後5秒接圖片
                    loop_dur = max(0, audio_duration - 5)
                    bg_video_looped = bg_video_clip.with_effects([vfx.Loop(duration=loop_dur)])
                    
                    target_img = img_clip_list[-1]
                    bg_img_clip = ImageClip(target_img).with_duration(5).resized(TARGET_RESOLUTION).with_effects([vfx.CrossFadeIn(1.0)])
                    
                    bg_clip = concatenate_videoclips([bg_video_looped, bg_img_clip], padding=-1.0, method="compose")
                else:
                    # 只有影片 => Loop播滿
                    bg_clip = bg_video_clip.with_effects([vfx.Loop(duration=audio_duration)])
            else:
                if len(img_clip_list) > 0:
                    # 只有圖片 => 均分圖片顯示時間
                    time_per_image = audio_duration / len(img_clip_list)
                    processed_clips = []
                    for i, img_path in enumerate(img_clip_list):
                        clip = ImageClip(img_path).with_duration(time_per_image).resized(TARGET_RESOLUTION)
                        if i > 0:
                            processed_clips.append(clip.with_effects([vfx.CrossFadeIn(1.0)]))
                        else:
                            processed_clips.append(clip)
                    bg_clip = concatenate_videoclips(processed_clips, padding=-1.0, method="compose")
                else:
                    # 完全沒畫面，給黑屏
                    black_frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
                    bg_clip = ImageClip(black_frame).with_duration(audio_duration)
            
            # --- 合聲音樂 ---
            final_audio = audio_clip
            if custom_music == 1 and news_id:
                asset_mp3 = os.path.join("assets", f"ID{news_id}.mp3")
                if os.path.exists(asset_mp3):
                    bgm_clip = AudioFileClip(asset_mp3)
                    if bgm_clip.duration is not None and bgm_clip.duration < audio_duration:
                        bgm_clip = bgm_clip.with_effects([
                            afx.AudioLoop(duration=audio_duration),
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    else:
                        bgm_clip = bgm_clip.with_duration(audio_duration).with_effects([
                            afx.MultiplyVolume(config.BGM_VOLUME)
                        ])
                    final_audio = CompositeAudioClip([bgm_clip, audio_clip]).with_duration(audio_duration)
                else:
                    print(f"  ⚠️ 無法找到素材音樂 {asset_mp3}")
            
            bg_clip = bg_clip.with_audio(final_audio)
            final_clips = [bg_clip]

        # 4. 疊加頭像
        add_avatar = False
        if mode in [1, 2]:
            add_avatar = has_avatar
        elif mode == 4:
            add_avatar = has_avatar and (custom_anchor == 1)

        if add_avatar:
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
                            .with_position(("center", 1350))) 
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
            final_video.write_videofile(out_path, fps=FPS, codec="h264_amf", audio_codec="aac", preset="balanced", logger="bar")
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
        
        # 7. 釋放記憶體與關閉所有檔案控制代碼，避免 WinError 6 錯誤
        print(f"  🧹 正在清理暫存資源...")
        
        # 關閉最終組合影片
        final_video.close()
        
        # 逐一關閉所有加入組合的片段 (包含字幕、頭像、背景)
        for clip in final_clips:
            try:
                clip.close()
            except:
                pass
        
        # 關閉額外開啟的檔案
        if bgm_clip:
            try: bgm_clip.close()
            except: pass
        if bg_video:
            try: bg_video.close()
            except: pass
        
        # 關閉原始音檔
        audio_clip.close()
        
        # 如果有 concatenated 的背景，也嘗試釋放其內部的 clips
        if 'bg_clip' in locals() and bg_clip:
            try: bg_clip.close()
            except: pass
        
        # 強制進行垃圾回收，幫助 Windows 釋放 Handle
        import gc
        gc.collect()
        
    print("\n🎉 所有影片合成暨字幕壓製完畢！")

if __name__ == "__main__":
    main()
