import os
import glob
import sys

# 修正 Windows 終端機印出 Emoji 的編碼問題
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
#  🎬 模組六：影片自動生成中心
#  小花的AI情報站 - AI Content Pipeline
# ============================================================

try:
    from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    print("❌ 找不到 moviepy 套件，請執行: pip install moviepy")
    sys.exit(1)

# --- 路徑與相關設定 ---
VOICES_DIR  = "output_voices"
IMAGES_DIR  = "output_images"
VIDEOS_DIR  = "output_videos"
AVATAR_PATH = "sample.png"

TARGET_RESOLUTION = (1080, 1920)  # 直式短影音 9:16
FPS = 24  # 日後如有動態元件比較順暢，目前雖然是靜態圖片但也設定 24

def extract_image_index(filepath: str) -> int:
    """處理像 script_Finance_6_0.jpg 這樣的檔名，抽取出後面的數字，以作為排序基準"""
    basename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(basename)[0]
    try:
        idx_str = name_no_ext.split("_")[-1]
        return int(idx_str)
    except ValueError:
        return 0

def main():
    print("========================================")
    print("  🎬 AI 影片自動生成中心 (Video Assembly)")
    print("========================================")

    # 確保輸出目錄存在
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    # 尋找所有音訊檔，代表著已就緒可以合成影片的腳本
    voice_files = glob.glob(os.path.join(VOICES_DIR, "*_final.wav"))

    if not voice_files:
        print(f"❌ 在 '{VOICES_DIR}/' 中找不到 *_final.wav 音檔。")
        print("   請確認 step3 已經執行完畢！")
        return

    # 確認有沒有虛擬頭像素材
    has_avatar = os.path.exists(AVATAR_PATH)
    if not has_avatar:
        print(f"⚠️ 找不到虛擬頭像檔 '{AVATAR_PATH}'，將純粹播放新聞配圖底檔。")

    for v_path in voice_files:
        # v_path 範例：output_voices/script_Finance_6_final.wav
        # 取出 base name: script_Finance_6
        basename = os.path.basename(v_path).replace("_final.wav", "")
        print(f"\n▶ 正在合成：{basename}")
        
        # 1. 讀取音訊檔
        audio_clip = AudioFileClip(v_path)
        audio_duration = audio_clip.duration
        
        # 2. 尋找對應的圖片
        pattern = os.path.join(IMAGES_DIR, f"{basename}_*.jpg")
        img_paths = glob.glob(pattern)
        
        if not img_paths:
            print(f"  ❌ 找不到對應此語音的背景圖片：{pattern}")
            print("     跳過這個腳本...")
            continue
            
        # 依照圖片編號排序，確保 _0, _1, _2 的順序正確
        img_paths = sorted(img_paths, key=extract_image_index)
        
        # 計算每張圖分配到的時間
        time_per_image = audio_duration / len(img_paths)
        
        print(f"  🖼 找到 {len(img_paths)} 張背景圖，每張圖將顯示 {time_per_image:.1f} 秒...")
        
        image_clips = []
        for img_path in img_paths:
            # 讀取圖片，設定長度，並對齊縮放為 1080x1920
            clip = (ImageClip(img_path)
                    .with_duration(time_per_image)
                    .resized(TARGET_RESOLUTION))
            image_clips.append(clip)
            
        # 3. 組合所有背景片斷，加入淡入轉場
        import moviepy.video.fx as vfx
        processed_clips = []
        for i, clip in enumerate(image_clips):
            if i > 0:
                # 第二張之後的圖片，前 1 秒做淡入轉場 (避免太突兀)
                processed_clips.append(clip.with_effects([vfx.CrossFadeIn(1.0)]))
            else:
                processed_clips.append(clip)
                
        bg_clip = concatenate_videoclips(processed_clips, padding=-1.0, method="compose")
        bg_clip = bg_clip.with_audio(audio_clip) # 將語音軌綁定上去
        
        final_clips = [bg_clip]
        
        # 4. 若有頭像，則疊加上去
        if has_avatar:
            print("  🙎‍♀️ 疊加動態/虛擬圖相 (此版本為靜態圖片 sample.png)...")
            # 縮放頭像，並將其置放於畫面右下角
            # with_position 可吃 ("right", "bottom")
            avatar_clip = (ImageClip(AVATAR_PATH)
                           .resized(width=680)  # 頭像寬度設定為 680 像素 (佔畫面 1/4 面積略小，吻合去背後的 sample 圖)
                           .with_duration(audio_duration)
                           .with_position(("right", "bottom")))
            final_clips.append(avatar_clip)
            
        # 5. 生成最終成果圖層
        final_video = CompositeVideoClip(final_clips, size=TARGET_RESOLUTION)
        
        out_path = os.path.join(VIDEOS_DIR, f"{basename}.mp4")
        print(f"  🎥 開始寫入影片: {out_path} ...\n")
        
        success = False
        try:
            # 優先嘗試 AMD 硬體編碼
            print("  ⚡ 嘗試使用 AMD GPU 硬體加速編碼...")
            final_video.write_videofile(out_path, fps=FPS, codec="h264_amf", audio_codec="aac", logger="bar")
            success = True
        except Exception as e:
            print(f"  ⚠️ AMD 硬解不支援此電腦 ({e})，切換至標準 CPU 模式...")
            
        if not success:
            final_video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", logger="bar")
        
        # 釋放資源
        audio_clip.close()
        final_video.close()
        
    print("\n🎉 所有影片合成完畢！")

if __name__ == "__main__":
    main()
